/* Shared calculations for the browser dashboard and independent validation. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.OlistMetrics = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function integer(value, label, minimum = 0) {
    if (!Number.isSafeInteger(value) || value < minimum) {
      throw new RangeError(`${label} must be a safe integer >= ${minimum}`);
    }
    return value;
  }

  function add(a, b) {
    return integer(a + b, 'Aggregate');
  }

  // Round exact integer ratios at the display boundary; 9.825 becomes 9.83.
  function halfUp(numerator, denominator, places = 2) {
    integer(numerator, 'Numerator');
    integer(denominator, 'Denominator');
    integer(places, 'Decimal places');
    if (places > 6) throw new RangeError('At most six decimal places are supported');
    if (denominator === 0) return null;
    const scale = 10n ** BigInt(places);
    const n = BigInt(numerator) * scale;
    const d = BigInt(denominator);
    const rounded = (2n * n + d) / (2n * d);
    if (rounded > BigInt(Number.MAX_SAFE_INTEGER)) throw new RangeError('Rounded value exceeds safe precision');
    return Number(rounded) / Number(scale);
  }

  function percent(numerator, denominator) {
    return halfUp(integer(numerator * 100, 'Percentage numerator'), denominator);
  }

  function indices(fields, required) {
    if (!Array.isArray(fields) || new Set(fields).size !== fields.length) {
      throw new TypeError('Payload fields must be a list of unique names');
    }
    const result = {};
    for (const name of required) {
      const index = fields.indexOf(name);
      if (index < 0) throw new TypeError(`Missing payload field: ${name}`);
      result[name] = index;
    }
    return result;
  }

  function labelCompare(a, b) {
    return a < b ? -1 : a > b ? 1 : 0;
  }

  function salesAccumulator() {
    return { orders: 0, cents: 0 };
  }

  function addSale(target, cents) {
    target.orders += 1;
    target.cents = add(target.cents, cents);
  }

  function finishSales(target) {
    const aovCents = halfUp(target.cents, target.orders, 0);
    return { ...target, value: target.cents / 100, aov: aovCents === null ? null : aovCents / 100 };
  }

  function deliveryAccumulator() {
    return { orders: 0, lateOrders: 0, elapsedSeconds: 0, positiveDelayDays: 0 };
  }

  function addDelivery(target, row, field) {
    if (row[field.late] !== 0 && row[field.late] !== 1) {
      throw new RangeError('Eligible delivery requires a 0/1 late flag');
    }
    target.orders += 1;
    target.elapsedSeconds = add(target.elapsedSeconds, integer(row[field.deliverySeconds], 'Delivery seconds'));
    if (row[field.late] === 1) {
      target.lateOrders += 1;
      target.positiveDelayDays = add(target.positiveDelayDays, integer(row[field.delayDays], 'Positive delay days', 1));
    }
  }

  function finishDelivery(target) {
    return {
      ...target,
      onTimeOrders: target.orders - target.lateOrders,
      latePct: percent(target.lateOrders, target.orders),
      averageDays: halfUp(target.elapsedSeconds, integer(target.orders * 86400, 'Delivery denominator')),
      averagePositiveDelayDays: halfUp(target.positiveDelayDays, target.lateOrders),
    };
  }

  function reviewAccumulator() {
    return { salesOrders: 0, reviewedOrders: 0, scoreSum: 0, lowScoreOrders: 0 };
  }

  function addReview(target, score) {
    target.salesOrders += 1;
    if (score !== null) {
      integer(score, 'Review score', 1);
      if (score > 5) throw new RangeError('Review score must be 1–5 or null');
      target.reviewedOrders += 1;
      target.scoreSum = add(target.scoreSum, score);
      if (score <= 2) target.lowScoreOrders += 1;
    }
  }

  function finishReviews(target) {
    return {
      ...target,
      missingReviewOrders: target.salesOrders - target.reviewedOrders,
      reviewCoveragePct: percent(target.reviewedOrders, target.salesOrders),
      averageScore: halfUp(target.scoreSum, target.reviewedOrders),
      lowScorePct: percent(target.lowScoreOrders, target.reviewedOrders),
    };
  }

  function group(map, key, create) {
    if (!map.has(key)) map.set(key, create());
    return map.get(key);
  }

  function descendingRatio(aCount, aTotal, bCount, bTotal) {
    if (!aTotal && !bTotal) return 0;
    if (!aTotal) return 1;
    if (!bTotal) return -1;
    const difference = BigInt(bCount) * BigInt(aTotal) - BigInt(aCount) * BigInt(bTotal);
    return difference < 0n ? -1 : difference > 0n ? 1 : 0;
  }

  function sortDelivery(a, b) {
    return b.lateOrders - a.lateOrders ||
      descendingRatio(a.lateOrders, a.orders, b.lateOrders, b.orders) || labelCompare(a.label, b.label);
  }

  function compute(payload, suppliedFilters = {}) {
    if (!payload || !Array.isArray(payload.orders) || !Array.isArray(payload.categories)) {
      throw new TypeError('Expected the exported Olist orders and category rows');
    }
    const field = indices(payload.fields, ['month', 'state', 'customer', 'status', 'salesCents',
      'sales', 'delivery', 'late', 'deliverySeconds', 'delayDays', 'reviewScore', 'preDeliveryReview']);
    const categoryField = indices(payload.categoryFields, ['order', 'category', 'salesCents', 'itemCount', 'delivery']);
    const startMonth = Number(suppliedFilters.startMonth ?? 0);
    const endMonth = Number(suppliedFilters.endMonth ?? (payload.months.length - 1));
    integer(startMonth, 'Start month');
    integer(endMonth, 'End month');
    if (startMonth > endMonth || endMonth >= payload.months.length) throw new RangeError('Invalid purchase-month range');
    const state = suppliedFilters.state === undefined || suppliedFilters.state === 'all'
      ? 'all' : Number(suppliedFilters.state);
    if (state !== 'all') {
      integer(state, 'State index');
      if (state >= payload.states.length) throw new RangeError('Unknown state index');
    }
    const filters = { startMonth, endMonth, state };
    const selected = new Uint8Array(payload.orders.length);
    let selectedOrders = 0;
    let nonDeliveredOrders = 0;
    let invalidDateOrders = 0;
    const sales = salesAccumulator();
    const delivery = deliveryAccumulator();
    const reviews = reviewAccumulator();
    const customerGroups = new Map();
    const salesStates = new Map();
    const deliveryStates = new Map();
    const reviewStates = new Map();
    const salesCategories = new Map();
    const deliveryCategories = new Map();
    const distributionCounts = [0, 0, 0, 0, 0, 0];
    const comparison = [
      { key: 'on_time', label: 'On time', ...reviewAccumulator(), preDeliveryReviewOrders: 0 },
      { key: 'late', label: 'Late', ...reviewAccumulator(), preDeliveryReviewOrders: 0 },
    ];
    const monthly = Array.from({ length: endMonth - startMonth + 1 }, (_, index) => {
      const monthIndex = startMonth + index;
      return { monthIndex, month: payload.months[monthIndex], allOrders: 0,
        sales: salesAccumulator(), delivery: deliveryAccumulator() };
    });

    for (let index = 0; index < payload.orders.length; index += 1) {
      const row = payload.orders[index];
      const monthIndex = row[field.month];
      const stateId = row[field.state];
      if (monthIndex < startMonth || monthIndex > endMonth || (state !== 'all' && state !== stateId)) continue;
      selected[index] = 1;
      selectedOrders += 1;
      const month = monthly[monthIndex - startMonth];
      month.allOrders += 1;
      const stateLabel = payload.states[stateId];
      if (typeof stateLabel !== 'string') throw new RangeError('Order references an unknown state');
      if (payload.statuses[row[field.status]] !== 'delivered') nonDeliveredOrders += 1;
      else if (row[field.delivery] !== 1) invalidDateOrders += 1;

      if (row[field.sales] === 1) {
        const cents = integer(row[field.salesCents], 'Sales cents');
        const score = row[field.reviewScore];
        addSale(sales, cents);
        addSale(month.sales, cents);
        addSale(group(salesStates, stateId, () => ({ stateId, label: stateLabel, ...salesAccumulator() })), cents);
        addReview(reviews, score);
        addReview(group(reviewStates, stateId, () => ({ stateId, label: stateLabel, ...reviewAccumulator() })), score);
        distributionCounts[score === null ? 5 : score - 1] += 1;
        const customerId = integer(row[field.customer], 'Customer index');
        const customer = group(customerGroups, customerId, () => ({ customerId,
          label: `Customer ${String(customerId + 1).padStart(6, '0')}`,
          ...salesAccumulator(), ...reviewAccumulator() }));
        addSale(customer, cents);
        addReview(customer, score);
        if (row[field.delivery] === 1) {
          const comparisonGroup = comparison[row[field.late]];
          if (!comparisonGroup) throw new RangeError('Eligible delivery requires a 0/1 late flag');
          addReview(comparisonGroup, score);
          if (score !== null && row[field.preDeliveryReview] === 1) comparisonGroup.preDeliveryReviewOrders += 1;
        }
      }
      if (row[field.delivery] === 1) {
        addDelivery(delivery, row, field);
        addDelivery(month.delivery, row, field);
        addDelivery(group(deliveryStates, stateId,
          () => ({ stateId, label: stateLabel, ...deliveryAccumulator() })), row, field);
      }
    }

    // The export contains one row per order/category. Item multiplicity is a
    // separate count; an order's full value is never copied into each category.
    const categoryPairs = new Set();
    for (const categoryRow of payload.categories) {
      const orderIndex = integer(categoryRow[categoryField.order], 'Category order reference');
      if (orderIndex >= payload.orders.length) throw new RangeError('Category references an unknown order');
      if (!selected[orderIndex]) continue;
      const categoryId = integer(categoryRow[categoryField.category], 'Category index');
      const label = payload.categoryLabels[categoryId];
      if (typeof label !== 'string') throw new RangeError('Unknown category index');
      const pair = `${orderIndex}:${categoryId}`;
      if (categoryPairs.has(pair)) throw new TypeError('Duplicate order/category pair in exported data');
      categoryPairs.add(pair);
      const order = payload.orders[orderIndex];
      if (order[field.sales] === 1 && categoryRow[categoryField.salesCents] !== null) {
        const category = group(salesCategories, categoryId,
          () => ({ categoryId, label, ...salesAccumulator(), itemCount: 0 }));
        addSale(category, integer(categoryRow[categoryField.salesCents], 'Category cents'));
        category.itemCount = add(category.itemCount, integer(categoryRow[categoryField.itemCount], 'Category item count', 1));
      }
      if (order[field.delivery] === 1 && categoryRow[categoryField.delivery] === 1) {
        addDelivery(group(deliveryCategories, categoryId,
          () => ({ categoryId, label, ...deliveryAccumulator() })), order, field);
      }
    }

    let repeatCustomers = 0;
    let repeatOrders = 0;
    let repeatCents = 0;
    for (const customer of customerGroups.values()) {
      if (customer.orders >= 2) {
        repeatCustomers += 1;
        repeatOrders += customer.orders;
        repeatCents = add(repeatCents, customer.cents);
      }
    }
    const uniqueCustomers = customerGroups.size;
    const salesStateRows = [...salesStates.values()].map(finishSales)
      .map(row => ({ ...row, sharePct: percent(row.cents, sales.cents) }))
      .sort((a, b) => b.cents - a.cents || labelCompare(a.label, b.label));
    const salesCategoryRows = [...salesCategories.values()]
      .map(row => ({ ...row, value: row.cents / 100, sharePct: percent(row.cents, sales.cents) }))
      .sort((a, b) => b.cents - a.cents || labelCompare(a.label, b.label));
    const reviewStateRows = [...reviewStates.values()].map(finishReviews).sort((a, b) =>
      b.lowScoreOrders - a.lowScoreOrders ||
      descendingRatio(a.lowScoreOrders, a.reviewedOrders, b.lowScoreOrders, b.reviewedOrders) || labelCompare(a.label, b.label));
    const topSpenders = [...customerGroups.values()].sort((a, b) => b.cents - a.cents || a.customerId - b.customerId)
      .slice(0, 20).map(customer => {
        const amounts = finishSales(customer);
        return { customerId: customer.customerId, label: customer.label,
          orders: customer.orders, cents: customer.cents, value: amounts.value, aov: amounts.aov,
          reviewedOrders: customer.reviewedOrders,
          averageScore: halfUp(customer.scoreSum, customer.reviewedOrders),
          reviewCoveragePct: percent(customer.reviewedOrders, customer.orders) };
      });

    return {
      filters,
      selectedOrders,
      sales: {
        ...finishSales(sales), uniqueCustomers, excludedOrders: selectedOrders - sales.orders,
        monthly: monthly.map(month => ({ monthIndex: month.monthIndex, month: month.month,
          allOrders: month.allOrders, ...finishSales(month.sales), excludedOrders: month.allOrders - month.sales.orders })),
        categories: salesCategoryRows, states: salesStateRows,
      },
      delivery: {
        ...finishDelivery(delivery), excludedOrders: selectedOrders - delivery.orders,
        nonDeliveredOrders, invalidDateOrders,
        monthly: monthly.map(month => ({ monthIndex: month.monthIndex, month: month.month,
          allOrders: month.allOrders, ...finishDelivery(month.delivery),
          excludedOrders: month.allOrders - month.delivery.orders })),
        states: [...deliveryStates.values()].map(finishDelivery).sort(sortDelivery),
        categories: [...deliveryCategories.values()].map(finishDelivery).sort(sortDelivery),
      },
      customers: {
        ...finishReviews(reviews), uniqueCustomers,
        oneTimeCustomers: uniqueCustomers - repeatCustomers,
        repeatCustomers, repeatCustomerPct: percent(repeatCustomers, uniqueCustomers),
        repeatOrders, repeatCents, repeatOrderPct: percent(repeatOrders, sales.orders),
        repeatSalesPct: percent(repeatCents, sales.cents),
        distribution: distributionCounts.map((orders, index) => ({ score: index === 5 ? null : index + 1,
          label: index === 5 ? 'No eligible selected review' : String(index + 1), orders,
          shareOfSalesPct: percent(orders, sales.orders),
          shareOfReviewedPct: index === 5 ? null : percent(orders, reviews.reviewedOrders) })),
        deliveryComparison: comparison.map(finishReviews), states: reviewStateRows, topSpenders,
      },
    };
  }

  return Object.freeze({ compute, halfUp });
});
