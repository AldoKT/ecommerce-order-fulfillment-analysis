# Day 1 cleaning and analytical modeling rules

This document describes the reproducible transformations in `python/02_data_cleaning.ipynb`. The notebook reads only from `data/raw` and writes only the requested CSV outputs under `data/processed`. It does not modify raw files or perform business analysis.

## Output table grains

| Output | Grain | Rows generated |
| --- | --- | ---: |
| `fact_orders` | Exactly one row per `order_id` | 99,441 |
| `fact_order_items` | Exactly one row per `order_id` + `order_item_id` | 112,650 |
| `dim_customers` | Exactly one row per `customer_id` | 99,441 |
| `dim_products` | Exactly one row per `product_id` | 32,951 |
| `dim_sellers` | Exactly one row per `seller_id` | 3,095 |

## Included and excluded records

- All 99,441 raw orders are retained, including cancelled, unavailable, and orders without item rows.
- All 112,650 raw order-item rows are retained. Items are not removed because a category is untranslated or missing.
- All raw customer, product, and seller dimension rows are retained.
- Payments and reviews are not emitted as standalone processed tables in this layer. They are aggregated by `order_id` before being joined to `fact_orders`.
- The raw geolocation table is not used in these outputs because no requested output requires a geolocation dimension.

## Missing-value rules

- Missing customer, product, seller, payment, or review relationships remain missing after a left join.
- `item_count`, `seller_count`, `category_count`, `payment_record_count`, and `review_count` are `0` when no related source rows exist.
- `category_count` is the number of distinct resolved display categories within an order. `Unknown` is a legitimate resolved display category and is counted.
- `merchandise_value`, item-level monetary fields, order-level `freight_value`, `payment_value`, and other monetary aggregates remain null when their related source records do not exist. Missing money is never converted to zero.
- `has_item_data` is true when an order has one or more item rows. `has_review_data` is true when an order has one or more review rows.
- Missing product physical measurements are preserved as missing. No physical attributes are imputed.
- `dim_customers` and `dim_sellers` retain ZIP prefixes as ZIP-prefix identifiers.

## Lifecycle calculation rules

Each duration is calculated only when both endpoint timestamps exist and the endpoint is not earlier than its start:

- `approval_hours` = approval timestamp minus purchase timestamp, in hours.
- `preparation_days` = carrier handoff timestamp minus approval timestamp, in days.
- `transportation_days` = customer delivery timestamp minus carrier handoff timestamp, in days.
- `total_lead_time_days` = customer delivery timestamp minus purchase timestamp, in days.

The validity flags are Pandas nullable BooleanDtype fields with three states: `True` means all required timestamps exist and the sequence is valid, `False` means all required timestamps exist and the sequence is invalid, and null means one or more required timestamps are missing. Invalid sequences produce a false flag and a null corresponding duration. The 1,359 carrier-before-approval records and 23 delivery-before-carrier records are retained; they are not deleted or corrected. Cancelled orders remain in `fact_orders`, but lifecycle durations are not intended for later delivery-duration KPIs without an explicit delivered-order population rule. After import, Power BI should explicitly assign the validity columns as Boolean/True-False fields so the three states remain intentional.

## Delivery-classification rules

- Classification is applied only when `order_status == delivered` and the customer delivery timestamp is present.
- Calendar dates are compared, not exact times of day.
- Delivery on the estimated delivery date has signed variance `0` and classification `On Time`.
- A negative or zero signed variance is `On Time`; a positive signed variance is `Late`.
- All other orders are `Not Classified`.
- `delivery_variance_days` = actual delivery calendar date minus estimated delivery calendar date.
- `delay_days` equals the signed variance only when it is positive. On-time and unclassified orders have null `delay_days`.

## Category fallback rules

- `product_category_original` retains the source Portuguese category, including nulls.
- `product_category_english` uses the translation table when available.
- For the 13 product rows in the 2 untranslated categories, the original Portuguese category is used as the display fallback.
- For null product categories, `product_category_english` is `Unknown`.
- Items are not deleted because their category is untranslated or missing.

## Review aggregation rule

Reviews are grouped by `order_id` before joining to orders. `review_count` is the number of review rows and `average_review_score` is the arithmetic mean of `review_score`. Review detail is never joined directly to item or payment detail.

## Anomaly-handling rules

- Raw values are not corrected, deleted, or overwritten.
- One-to-many item, payment, and review sources are aggregated independently before order-level joins to prevent order-count inflation and cross-product duplication.
- Invalid lifecycle sequences remain visible through validity flags and null durations.
- Orders without items, payments, or reviews remain in the order fact with the missing-value rules above.

## Monetary-value rules

- Item `price` and `freight_value` are retained at native item grain.
- `fact_orders.merchandise_value` is the sum of item `price` by `order_id` when item rows exist.
- `fact_orders.freight_value` is the sum of item freight by `order_id` when item rows exist.
- `fact_orders.payment_value` is the sum of payment `payment_value` by `order_id` when payment rows exist.
- No currency conversion, rounding, or imputation is applied.
- Monetary reconciliation uses `abs_tol = 1e-6` and `rel_tol = 0.0`. Each processed total is compared with its raw-source total using `abs(processed - raw) <= abs_tol + rel_tol * abs(raw)`.

## Validation results

The executed notebook completed with zero cell errors. All checks below passed:

| Validation | Result |
| --- | --- |
| `fact_orders` row count equals raw orders | PASS: 99,441 = 99,441 |
| `fact_orders.order_id` unique | PASS |
| `fact_order_items` row count equals raw order-items | PASS: 112,650 = 112,650 |
| `fact_order_items` composite key unique | PASS |
| Dimension keys unique | PASS for customers, products, and sellers |
| No order count inflation after aggregate joins | PASS: 99,441 rows |
| Item price sum matches raw item price sum within tolerance | PASS |
| Item freight sum matches raw freight sum within tolerance | PASS |
| Non-null order merchandise sum matches raw item price total within tolerance | PASS |
| Non-null order freight sum matches raw freight total within tolerance | PASS |
| Order payment totals match raw payment table within tolerance | PASS |
| Classification values limited to three allowed values | PASS |
| Same-date deliveries classified On Time | PASS: 1,292 orders |
| Invalid sequences have null corresponding durations | PASS for approval, preparation, and transportation checks |
| Processed outputs have no duplicate column names | PASS |

Invalid sequence counts observed in the raw data are 0 approval-before-purchase, 1,359 carrier-before-approval, and 23 delivery-before-carrier. The source contains 99,224 review rows as read by pandas. The category-count correction changes 1,451 orders, corresponding to orders whose resolved display categories now include `Unknown`. Observed monetary differences are 0.0 for item price, item freight, order merchandise, order freight, and payment totals, all within the documented tolerance.

## Known limitations

- `dim_customers` is keyed by the order-level `customer_id`, so the same real-world customer can appear across multiple customer IDs.
- No geolocation aggregation is included in this requested layer.
- The dataset has 610 products with null source categories and 13 products in 2 non-translated categories; the specified display fallbacks preserve them but do not translate them.
- Lifecycle durations are timestamp differences and may be fractional days. Delivery classification intentionally uses calendar dates.
- Review and payment data are only represented through order-level aggregates in this layer. Detail-level payment and review facts would be a separate modeling scope.
- The notebook produces tables and validations only. It does not define delivery-duration KPI populations, interpret performance, or make recommendations.
