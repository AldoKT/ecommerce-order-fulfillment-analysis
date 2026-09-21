# Business recommendations

This is an observational portfolio analysis of the public Olist dataset. Findings identify priorities for investigation; they do not establish causes, ownership, or expected impact. Merchandise value is an item-price measure, not revenue or profit.

## Baseline metrics

The validated baseline is **99,441 total orders**, **96,478 delivered orders**, **96,470 classified orders**, **89,936 on-time orders**, and **6,534 late orders**: a **93.23% on-time delivery rate**. Average valid lead time is approximately **12.56 days** and average late delay is approximately **10.62 days**. There are **112,650 items**, **R$13,591,643.70** in merchandise value, and **R$2,251,909.54** in freight value. Repeat customers total **2,997 of 96,096** distinct customers (approximately **3.12%**).

## 1. March 2018 fulfillment performance

- **Observed finding:** March 2018 was the lowest qualifying complete purchase month at **81.04%** on time (7,003 classified orders). Partial boundary months **2016-09** and **2018-10** are excluded from comparison.
- **Interpretation:** The month is a useful priority cohort, not evidence of a specific failure mode.
- **Recommended action:** Review the March 2018 cohort by operational handoff, carrier, route, and promised-versus-actual milestone—if those fields can be obtained.
- **Metric to monitor:** Classified-order on-time rate, late-order count, and median/average delay by complete purchase month.
- **Limitation or evidence still needed:** Carrier assignment, fulfillment-center, inventory, holiday/promotion, route, and service-level data are needed to assess potential drivers.

## 2. AL customer-state performance

- **Observed finding:** AL had the lowest on-time rate among states with at least 100 classified orders: **78.59%** (85 late of 397 classified orders).
- **Interpretation:** This state-level pattern identifies where to investigate; it does not demonstrate that geography caused delays.
- **Recommended action:** Add an AL-focused operational review segmented by origin, destination region, carrier, and service level.
- **Metric to monitor:** AL classified-order on-time rate, late-order count, and delay days alongside the all-state baseline.
- **Limitation or evidence still needed:** Route distance, carrier/service data, delivery exceptions, and address-quality information are required for an operational explanation.

## 3. Late-order monitoring

- **Observed finding:** **6,534** of **96,470** classified orders were late; the on-time denominator intentionally excludes not-classified orders.
- **Interpretation:** A rate alone can conceal a changing volume of unclassifiable orders.
- **Recommended action:** Publish a recurring view with on-time rate, late count, classified count, not-classified count, and average late delay; alert on material deterioration after sufficient volume is reached.
- **Metric to monitor:** On-time rate (**93.23%** baseline), late count, average late delay (**10.62 days** baseline), and not-classified count.
- **Limitation or evidence still needed:** The dataset has no live event stream, alert thresholds, or agreed service target; operational owners must define these before automation.

## 4. Product-category freight burden

- **Observed finding:** Across items, freight totals **R$2,251,909.54** against **R$13,591,643.70** merchandise value. Category reporting is deliberately item-grain.
- **Interpretation:** Freight-to-merchandise differences describe commercial burden, not profit, customer price, or delivery performance.
- **Recommended action:** Prioritize high freight-to-merchandise categories for packaging, assortment, and fulfillment-network review while preserving item-grain definitions.
- **Metric to monitor:** Freight-to-merchandise ratio, item count, merchandise value, and freight value by category.
- **Limitation or evidence still needed:** Package dimensions, weight, shipping contracts, subsidies, margin, and returns data are required to assess economics or choose an intervention.

## 5. Seller-state concentration

- **Observed finding:** Seller state SP accounts for the largest observed item-grain merchandise value and item volume in the seller-state summary.
- **Interpretation:** Concentration can indicate exposure to disruption; it does not show that sellers in SP create delay or freight outcomes.
- **Recommended action:** Track concentration by seller state and assess contingency coverage for material concentrations.
- **Metric to monitor:** Seller-state share of items, merchandise value, and freight value; report delivery separately at order grain.
- **Limitation or evidence still needed:** Seller capacity, stock location, fulfillment-node, carrier, and route data are needed to evaluate resilience or causal mechanisms.

## 6. Repeat-customer rate

- **Observed finding:** **2,997 of 96,096** distinct customers had more than one order, an approximately **3.12%** repeat-customer rate.
- **Interpretation:** This is a descriptive rate based on `customer_unique_id`; it does not measure retention quality or explain repeat behavior.
- **Recommended action:** Establish a cohort-based repeat-purchase view with a defined observation window before setting a retention objective.
- **Metric to monitor:** Repeat-customer rate, repeat order count, and time to next order by purchase cohort.
- **Limitation or evidence still needed:** Acquisition channel, customer tenure, marketing exposure, cancellations, and a longer observation window are needed for retention interpretation.

## 7. Lifecycle timestamp quality

- **Observed finding:** The source retains 160 missing approval timestamps, 1,783 missing carrier-handoff timestamps, 2,965 missing delivery timestamps, 1,359 invalid preparation sequences, and 23 invalid transportation sequences.
- **Interpretation:** These are data-quality diagnostics; they should not be silently repaired or treated as proof of process failure.
- **Recommended action:** Instrument timestamp capture and sequence validation at source, retain nulls distinctly from invalid sequences, and reconcile exceptions with source-system owners.
- **Metric to monitor:** Missingness and invalid-sequence rates by lifecycle field, plus the not-classified-order count.
- **Limitation or evidence still needed:** Event-generation rules, source-system lineage, timezone treatment, and correction/audit policies are needed before attributing anomalies to operations.
