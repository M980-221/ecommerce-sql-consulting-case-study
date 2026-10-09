// Node DOM fixtures verify templates and event wiring, not browser layout.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import test from 'node:test';

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'dashboard/index.html'), 'utf8');
require('../dashboard/data.js');
const data = globalThis.OLIST_DATA;
const metrics = require('../dashboard/metrics.js');
const ui = require('../dashboard/app.js');
const defaultSnapshot = metrics.compute(data);

class Element {
  constructor(attributes = {}) {
    this.attributes = { ...attributes };
    this.innerHTML = '';
    this.textContent = '';
    this.value = '';
    this.disabled = true;
    this.listeners = {};
    this.children = [];
  }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  removeAttribute(key) { delete this.attributes[key]; }
  addEventListener(type, callback) { (this.listeners[type] ??= []).push(callback); }
  dispatch(type, properties = {}) {
    for (const callback of this.listeners[type] ?? []) callback({ target: this, preventDefault() {}, ...properties });
  }
  appendChild(element) { this.children.push(element); }
  click() { this.clicked = true; this.dispatch('click'); }
  remove() { this.removed = true; }
  focus() { this.focused = true; }
  closest(selector) { return selector === '[data-expand]' && this.getAttribute('data-expand') ? this : null; }
  querySelector(selector) {
    const id = selector.match(/^\[data-expand="([^"]+)"\]$/)?.[1];
    return id && this.innerHTML.includes(`data-expand="${id}"`) ? new Element({ 'data-expand': id }) : null;
  }
}

function fixture(hash = '#sales') {
  const elements = Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m => [m[1], new Element({ id: m[1] })]));
  const nav = [...html.matchAll(/\bdata-page="([^"]+)"/g)].map(m => new Element({ 'data-page': m[1] }));
  const doc = { title: '', body: new Element(), getElementById: id => elements[id],
    querySelectorAll: selector => selector === '[data-page]' ? nav : [], createElement: () => new Element() };
  const listeners = {}, blobs = [], revoked = [];
  let currentHash = hash;
  const location = { get hash() { return currentHash; }, set hash(value) { currentHash = value.startsWith('#') ? value : '#' + value; } };
  const win = { location, Blob, URL: { createObjectURL(blob) { blobs.push(blob); return 'blob:fixture'; },
    revokeObjectURL(url) { revoked.push(url); } }, setTimeout(callback) { callback(); },
    addEventListener(type, callback) { listeners[type] = callback; } };
  const controller = ui.init({ doc, win, data, metrics });
  return { elements, nav, doc, win, controller, listeners, blobs, revoked };
}

test('all three real-data templates show checked headlines without undefined or nonfinite output', () => {
  const expected = { sales: ['12,230,652.13', '89,110', '137.25'],
    delivery: ['6.86%', '12.88', '10.98'], customers: ['4.15', '99.31%', '2.97%', '4,274'] };
  for (const [page, values] of Object.entries(expected)) {
    const markup = ui.renderPage(page, defaultSnapshot, data);
    for (const value of values) assert.ok(markup.includes(value), `${page}: ${value}`);
    assert.doesNotMatch(markup, /NaN|Infinity|>undefined</);
    assert.match(markup, /<table/);
  }
});

test('month and state change events recompute the selected rows and displayed values', () => {
  const f = fixture();
  f.elements['month-from'].value = String(data.months.indexOf('2018-03'));
  f.elements['month-from'].dispatch('change');
  f.elements['month-to'].value = String(data.months.indexOf('2018-03'));
  f.elements['month-to'].dispatch('change');
  f.elements['buyer-state'].value = String(data.states.indexOf('RJ'));
  f.elements['buyer-state'].dispatch('change');
  const snapshot = f.controller.getState().snapshot;
  assert.equal(snapshot.selectedOrders, 907);
  assert.equal(snapshot.sales.orders, 864);
  assert.equal(snapshot.customers.repeatCustomers, 14);
  assert.match(f.elements.report.innerHTML, /113,062\.84/);
  assert.match(f.elements['period-label'].textContent, /March 2018.*RJ/);
  assert.equal(f.elements.reset.disabled, false);
});

test('navigation and hash changes preserve filters; reset restores the full population', () => {
  const f = fixture('#customers');
  assert.equal(f.controller.getState().page, 'customers');
  f.controller.setFilters({ state: data.states.indexOf('SP') });
  f.nav.find(el => el.getAttribute('data-page') === 'delivery').click();
  assert.equal(f.controller.getState().page, 'delivery');
  assert.equal(f.controller.getState().snapshot.delivery.orders, 36952);
  assert.equal(f.win.location.hash, '#delivery');
  assert.equal(f.nav.filter(el => el.getAttribute('aria-current') === 'page').length, 1);
  f.win.location.hash = '#sales';
  f.listeners.hashchange();
  assert.equal(f.controller.getState().page, 'sales');
  f.elements.reset.click();
  assert.equal(f.controller.getState().snapshot.sales.orders, 89110);
  assert.equal(f.elements.reset.disabled, true);
});

test('crossing either month endpoint keeps the selection valid and synchronizes controls', () => {
  const f = fixture();
  f.controller.setFilters({ startMonth: 0, endMonth: 3 });
  f.elements['month-from'].value = '17';
  f.elements['month-from'].dispatch('change');
  assert.deepEqual(f.controller.getState().filters, { startMonth: 17, endMonth: 17, state: 'all' });
  assert.equal(f.elements['month-to'].value, '17');
  f.elements['month-to'].value = '0';
  f.elements['month-to'].dispatch('change');
  assert.deepEqual(f.controller.getState().filters, { startMonth: 0, endMonth: 0, state: 'all' });
});

test('the genuinely empty RR slice produces explicit empty states and dashes on every page', () => {
  const filters = { startMonth: data.months.indexOf('2017-08'), endMonth: data.months.indexOf('2017-08'), state: data.states.indexOf('RR') };
  const snapshot = metrics.compute(data, filters);
  assert.equal(snapshot.selectedOrders, 0);
  for (const page of Object.keys(ui.PAGES)) {
    const markup = ui.renderPage(page, snapshot, data);
    assert.match(markup, /No eligible|No observed/);
    assert.ok(markup.includes('—'));
    assert.doesNotMatch(markup, /NaN|Infinity|>undefined</);
  }
});

test('CSV download uses the current page and filters, creates a blob and revokes its URL', async () => {
  const f = fixture('#customers');
  const march = data.months.indexOf('2018-03');
  f.controller.setFilters({ startMonth: march, endMonth: march, state: data.states.indexOf('RJ') });
  const output = f.controller.download();
  assert.equal(output.filename, 'olist-customers-2018-03-to-2018-03-RJ.csv');
  assert.match(output.csv, /headline,selection,repeatCustomers,14,count,2018-03,2018-03,RJ/);
  assert.doesNotMatch(output.csv, /monthly_sales/);
  assert.equal(f.blobs.length, 1);
  assert.match(await f.blobs[0].text(), /repeatCustomers,14/);
  assert.equal(f.doc.body.children[0].clicked, true);
  assert.deepEqual(f.revoked, ['blob:fixture']);
});

test('show-all event expands an actual ranking and can collapse it again', () => {
  const f = fixture();
  const id = f.elements.report.innerHTML.match(/data-expand="([^"]+)"/)?.[1];
  assert.ok(id);
  const before = f.elements.report.innerHTML;
  const button = new Element({ 'data-expand': id });
  f.elements.report.dispatch('click', { target: button });
  assert.ok(f.elements.report.innerHTML.length > before.length);
  assert.match(f.elements.report.innerHTML, /aria-expanded="true"/);
  f.elements.report.dispatch('click', { target: button });
  assert.equal(f.elements.report.innerHTML, before);
});

test('local entry point loads the five required files in order with named form controls', () => {
  assert.deepEqual([...html.matchAll(/<script src="([^"]+)" defer/g)].map(m => m[1]), ['data.js', 'metrics.js', 'app.js']);
  for (const file of ['data.js', 'metrics.js', 'app.js', 'styles.css']) assert.ok(fs.existsSync(path.join(root, 'dashboard', file)));
  for (const id of ['month-from', 'month-to', 'buyer-state']) assert.match(html, new RegExp(`id="${id}"[^>]*aria-label=`));
  assert.match(html, /<noscript>/);
  assert.match(html, /aria-live="polite"/);
});

test('missing data shows a useful local-file recovery message instead of blank output', () => {
  const f = fixture();
  assert.equal(ui.init({ doc: f.doc, win: f.win, data: {}, metrics }), null);
  assert.match(f.elements.report.innerHTML, /keep index.html, data.js, metrics.js, app.js and styles.css together/);
  assert.equal(f.elements.report.getAttribute('aria-busy'), 'false');
});
