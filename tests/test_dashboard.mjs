import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { compute, halfUp } = require('../dashboard/metrics.js');

function fixture() {
  return {
    fields: ['month', 'state', 'customer', 'status', 'salesCents', 'sales', 'delivery',
      'late', 'deliverySeconds', 'delayDays', 'reviewScore', 'preDeliveryReview'],
    categoryFields: ['order', 'category', 'salesCents', 'itemCount', 'delivery'],
    months: Array.from({ length: 18 }, (_, month) => new Date(Date.UTC(2017, month + 1)).toISOString().slice(0, 7)),
    states: ['MG', 'RJ', 'SP'], statuses: ['canceled', 'delivered'],
    categoryLabels: ['Unknown category', 'books', 'home', 'Untranslated: pc_gamer'],
    orders: [
      // Month, state, persistent customer, status, cents, sales/delivery flags,
      // late flag, elapsed seconds, calendar delay, selected score, pre-receipt review.
      [0, 2, 0, 1, 3000, 1, 1, 0, 172800, 0, 5, 0],
      [0, 1, 0, 1, 1000, 1, 1, 1, 345600, 2, 1, 1],
      [1, 2, 1, 1, 0, 1, 1, 0, 86400, -1, null, 0],
      [1, 2, 2, 1, 2000, 1, 0, null, null, null, 3, 1],
      [0, 2, 0, 0, 9000, 0, 0, null, null, null, 1, 0],
      [2, 0, 4, 1, null, 0, 1, 1, 432000, 3, null, 0],
      [17, 1, 3, 1, 100, 1, 1, 0, 172800, 0, 5, 0],
    ],
    categories: [
      [0, 1, 2000, 2, 1], [0, 2, 1000, 1, 1],
      [1, 1, 1000, 1, 1], [2, 0, 0, 1, 1],
      [3, 2, 2000, 1, 0], [5, 0, null, 0, 1], [6, 3, 100, 1, 1],
    ],
  };
}

test('money and order counts stay at their own grains', () => {
  const result = compute(fixture());
  assert.equal(result.selectedOrders, 7);
  assert.equal(result.sales.orders, 5);
  assert.equal(result.sales.excludedOrders, 2);
  assert.equal(result.sales.cents, 6100);
  assert.equal(result.sales.value, 61);
  assert.equal(result.sales.aov, 12.2);
  assert.equal(result.sales.categories.reduce((total, row) => total + row.cents, 0), 6100);
  assert.equal(result.sales.categories.reduce((total, row) => total + row.orders, 0), 6);
  const books = result.sales.categories.find(row => row.label === 'books');
  assert.equal(books.orders, 2);
  assert.equal(books.itemCount, 3);
  assert.equal(books.cents, 3000);
});

test('month and state filters regenerate every headline from the selected orders', () => {
  const result = compute(fixture(), { startMonth: 0, endMonth: 1, state: 2 });
  assert.deepEqual(result.filters, { startMonth: 0, endMonth: 1, state: 2 });
  assert.equal(result.selectedOrders, 4);
  assert.equal(result.sales.orders, 3);
  assert.equal(result.sales.cents, 5000);
  assert.equal(result.sales.aov, 16.67);
  assert.equal(result.delivery.orders, 2);
  assert.equal(result.delivery.lateOrders, 0);
  assert.equal(result.customers.averageScore, 4);
  assert.equal(result.customers.reviewCoveragePct, 66.67);
  assert.equal(result.customers.repeatCustomers, 0);
  assert.equal(result.sales.categories.reduce((total, row) => total + row.cents, 0), 5000);
  assert.ok(result.sales.states.every(row => row.label === 'SP'));
});

test('all calendar months remain visible, and range endpoints are inclusive', () => {
  const result = compute(fixture());
  assert.equal(result.sales.monthly.length, 18);
  assert.equal(result.delivery.monthly.length, 18);
  assert.equal(result.sales.monthly[0].month, '2017-02');
  assert.equal(result.sales.monthly[17].month, '2018-07');
  assert.equal(result.sales.monthly[3].orders, 0);
  assert.equal(result.sales.monthly[3].aov, null);
  assert.equal(result.delivery.monthly[3].latePct, null);
  const last = compute(fixture(), { startMonth: 17, endMonth: 17 });
  assert.equal(last.sales.orders, 1);
  assert.equal(last.sales.cents, 100);
  assert.equal(last.sales.monthly.length, 1);
});

test('delivery uses exact elapsed seconds and averages delay among late orders only', () => {
  const result = compute(fixture());
  assert.equal(result.delivery.orders, 5);
  assert.equal(result.delivery.lateOrders, 2);
  assert.equal(result.delivery.onTimeOrders, 3);
  assert.equal(result.delivery.latePct, 40);
  assert.equal(result.delivery.averageDays, 2.8);
  assert.equal(result.delivery.positiveDelayDays, 5);
  assert.equal(result.delivery.averagePositiveDelayDays, 2.5);
  assert.equal(result.delivery.excludedOrders, 2);
  assert.equal(result.delivery.nonDeliveredOrders, 1);
  assert.equal(result.delivery.invalidDateOrders, 1);
});

test('category delivery counts an order once within each category while preserving overlap', () => {
  const result = compute(fixture());
  const books = result.delivery.categories.find(row => row.label === 'books');
  assert.equal(books.orders, 2);
  assert.equal(books.lateOrders, 1);
  assert.equal(books.latePct, 50);
  assert.equal(result.delivery.categories.reduce((total, row) => total + row.orders, 0), 6);
  assert.equal(result.delivery.orders, 5);
  const unknown = result.delivery.categories.find(row => row.label === 'Unknown category');
  assert.equal(unknown.orders, 2);
  assert.equal(unknown.lateOrders, 1);
  const duplicated = fixture();
  duplicated.categories.push([...duplicated.categories[0]]);
  assert.throws(() => compute(duplicated), /Duplicate order\/category pair/);
});

test('selected reviews use their own denominator and keep missing scores visible', () => {
  const customer = compute(fixture()).customers;
  assert.equal(customer.salesOrders, 5);
  assert.equal(customer.reviewedOrders, 4);
  assert.equal(customer.missingReviewOrders, 1);
  assert.equal(customer.reviewCoveragePct, 80);
  assert.equal(customer.scoreSum, 14);
  assert.equal(customer.averageScore, 3.5);
  assert.equal(customer.lowScoreOrders, 1);
  assert.equal(customer.lowScorePct, 25);
  assert.deepEqual(customer.distribution.map(row => row.orders), [1, 0, 1, 0, 2, 1]);
  assert.equal(customer.distribution[0].shareOfSalesPct, 20);
  assert.equal(customer.distribution[0].shareOfReviewedPct, 25);
  assert.equal(customer.distribution[5].shareOfReviewedPct, null);
});

test('delivery and review comparisons use the intersection and show response timing', () => {
  const [onTime, late] = compute(fixture()).customers.deliveryComparison;
  assert.deepEqual([onTime.key, late.key], ['on_time', 'late']);
  assert.equal(onTime.salesOrders, 3);
  assert.equal(onTime.reviewedOrders, 2);
  assert.equal(onTime.missingReviewOrders, 1);
  assert.equal(onTime.averageScore, 5);
  assert.equal(onTime.preDeliveryReviewOrders, 0);
  assert.equal(late.salesOrders, 1);
  assert.equal(late.reviewedOrders, 1);
  assert.equal(late.averageScore, 1);
  assert.equal(late.preDeliveryReviewOrders, 1);
});

test('repeat customer identity is regrouped after filtering, including separate same-month orders', () => {
  const customer = compute(fixture()).customers;
  assert.equal(customer.uniqueCustomers, 4);
  assert.equal(customer.repeatCustomers, 1);
  assert.equal(customer.repeatCustomerPct, 25);
  assert.equal(customer.repeatOrders, 2);
  assert.equal(customer.repeatCents, 4000);
  assert.equal(customer.repeatSalesPct, 65.57);
  // The two distinct purchases share one customer and month, across two states.
  const sameMonth = compute(fixture(), { startMonth: 0, endMonth: 0 }).customers;
  assert.equal(sameMonth.uniqueCustomers, 1);
  assert.equal(sameMonth.repeatCustomerPct, 100);
  const state = compute(fixture(), { state: 1 }).customers;
  assert.equal(state.uniqueCustomers, 2);
  assert.equal(state.repeatCustomers, 0);
});

test('weighted averages aggregate original totals rather than subgroup averages', () => {
  const result = compute(fixture());
  const nonemptyMonthly = result.sales.monthly.filter(row => row.orders);
  assert.equal(result.sales.aov, 12.2);
  assert.notEqual(result.sales.aov, nonemptyMonthly.reduce((sum, row) => sum + row.aov, 0) / nonemptyMonthly.length);
  assert.equal(result.delivery.averageDays, 2.8);
  assert.equal(result.customers.averageScore, 3.5);
});

test('empty selections retain zero counts, null means and all score buckets', () => {
  const result = compute(fixture(), { startMonth: 0, endMonth: 0, state: 0 });
  assert.equal(result.selectedOrders, 0);
  assert.equal(result.sales.cents, 0);
  assert.equal(result.sales.aov, null);
  assert.equal(result.delivery.latePct, null);
  assert.equal(result.delivery.averageDays, null);
  assert.equal(result.delivery.averagePositiveDelayDays, null);
  assert.equal(result.customers.averageScore, null);
  assert.equal(result.customers.repeatCustomerPct, null);
  assert.equal(result.customers.reviewCoveragePct, null);
  assert.equal(result.customers.distribution.length, 6);
  assert.ok(result.customers.distribution.every(row => row.orders === 0));
  assert.equal(result.customers.deliveryComparison.length, 2);
  assert.equal(result.sales.monthly.length, 1);
  assert.deepEqual(result.sales.categories, []);
  assert.deepEqual(result.delivery.categories, []);
  assert.deepEqual(result.customers.topSpenders, []);
});

test('exact half-up rounding handles halfway values and integer precision bounds', () => {
  assert.equal(halfUp(393, 40), 9.83);
  assert.equal(halfUp(5, 2, 0), 3);
  assert.equal(halfUp(0, 0), null);
  assert.throws(() => halfUp(Number.MAX_SAFE_INTEGER + 1, 1), /safe integer/);
  assert.throws(() => halfUp(1, -1), /safe integer/);
  const data = fixture();
  data.orders = [];
  data.categories = [];
  for (let index = 0; index < 40; index += 1) {
    data.orders.push([0, 2, index, 1, 1, 1, 1, 1, 864000, index === 39 ? 3 : 10, 5, 0]);
    data.categories.push([index, 1, 1, 1, 1]);
  }
  const result = compute(data);
  assert.equal(result.delivery.averagePositiveDelayDays, 9.83);
  assert.equal(result.delivery.categories[0].averagePositiveDelayDays, 9.83);
});

test('top spending ranks all filtered customers before taking twenty and breaks ties by ID', () => {
  const data = fixture();
  data.orders = [];
  data.categories = [];
  for (let index = 0; index < 25; index += 1) {
    data.orders.push([0, 2, index, 1, 100, 1, 1, 0, 86400, 0, null, 0]);
    data.categories.push([index, 1, 100, 1, 1]);
  }
  data.orders.push([0, 2, 24, 1, 100, 1, 1, 0, 86400, 0, 5, 0]);
  data.categories.push([25, 1, 100, 1, 1]);
  const result = compute(data).customers;
  assert.equal(result.uniqueCustomers, 25);
  assert.equal(result.topSpenders.length, 20);
  assert.equal(result.topSpenders[0].customerId, 24);
  assert.equal(result.topSpenders[0].label, 'Customer 000025');
  assert.equal(result.topSpenders[0].cents, 200);
  assert.equal(result.topSpenders[0].averageScore, 5);
  assert.equal(result.topSpenders[0].reviewCoveragePct, 50);
  assert.deepEqual(result.topSpenders.slice(1).map(row => row.customerId), Array.from({ length: 19 }, (_, i) => i));
});

test('invalid filters and unsafe input totals fail instead of displaying plausible numbers', () => {
  assert.throws(() => compute(fixture(), { startMonth: 5, endMonth: 4 }), /month range/);
  assert.throws(() => compute(fixture(), { endMonth: 18 }), /month range/);
  assert.throws(() => compute(fixture(), { state: 99 }), /state index/);
  const data = fixture();
  data.orders[0][4] = Number.MAX_SAFE_INTEGER;
  assert.throws(() => compute(data), /safe integer/);
});
