# Day 2 Power BI model specification

This specification covers the processed files in `data/processed/`. It describes the verified current data model and the approved Power BI implementation choices. It is not a claim that the model is a perfect star schema: `dim_customers` is an order-level customer-record table, and `fact_orders` is also the parent side of the order-item relationship.

## Tables, grains, and keys

| Table | File | Grain | Key |
| --- | --- | --- | --- |
| `fact_orders` | `data/processed/fact_orders.csv` | Exactly one row per order | `order_id` |
| `fact_order_items` | `data/processed/fact_order_items.csv` | Exactly one row per `order_id` + `order_item_id` | Composite: `order_id`, `order_item_id` |
| `dim_customers` | `data/processed/dim_customers.csv` | Exactly one row per order-level `customer_id` | `customer_id` |
| `dim_products` | `data/processed/dim_products.csv` | Exactly one row per product | `product_id` |
| `dim_sellers` | `data/processed/dim_sellers.csv` | Exactly one row per seller | `seller_id` |

Current verified row counts are 99,441 orders, 112,650 order items, 99,441 customer records, 32,951 products, and 3,095 sellers.

## Approved relationships

Create these five active relationships:

| From | To | Cardinality | Cross-filter direction | Active |
| --- | --- | --- | --- | --- |
| `dim_customers[customer_id]` | `fact_orders[customer_id]` | One-to-one | Both | Yes |
| `fact_orders[order_id]` | `fact_order_items[order_id]` | One-to-many | Single: `fact_orders` → `fact_order_items` | Yes |
| `dim_products[product_id]` | `fact_order_items[product_id]` | One-to-many | Single: `dim_products` → `fact_order_items` | Yes |
| `dim_sellers[seller_id]` | `fact_order_items[seller_id]` | One-to-many | Single: `dim_sellers` → `fact_order_items` | Yes |
| `DimDate[Date]` | `fact_orders[purchase_date]` | One-to-many | Single: `DimDate` → `fact_orders` | Yes |

Power BI requires Both cross-filtering for the approved one-to-one customer relationship. The `DimDate` table is a Power BI calculated table, not a processed CSV. Mark it as the model's date table using `DimDate[Date]`. Do not create relationships using city, state, category, ZIP prefix, or any other descriptive attribute. Do not relate on `customer_unique_id`; it is not unique and represents cross-order customer identity rather than the order-level relationship key.

### Date table

Create this calculated table in Power BI:

```DAX
DimDate =
VAR MinDate = MINX ( fact_orders, fact_orders[purchase_date] )
VAR MaxDate = MAXX ( fact_orders, fact_orders[purchase_date] )
RETURN
    ADDCOLUMNS (
        CALENDAR ( MinDate, MaxDate ),
        "Year", YEAR ( [Date] ),
        "Month Number", MONTH ( [Date] ),
        "Month Name", FORMAT ( [Date], "MMMM" ),
        "Year Month", FORMAT ( [Date], "YYYY-MM" ),
        "Year Month Sort", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
        "Quarter", "Q" & FORMAT ( [Date], "Q" )
    )
```

Mark `DimDate` as a date table using `DimDate[Date]`. Set `Month Name` to sort by `Month Number`, and set `Year Month` to sort by `Year Month Sort`. The verified purchase-date range is used for `MinDate` and `MaxDate`.

## Power BI data types

Import all identifier columns as Text, including ZIP prefixes. Import CSV timestamps explicitly as Date/Time and date-only fields as Date. Nullable Boolean fields must retain blank as null.

### `fact_orders`

| Column | Power BI type |
| --- | --- |
| `order_id` | Text |
| `customer_id` | Text |
| `customer_unique_id` | Text |
| `customer_city` | Text |
| `customer_state` | Text |
| `order_status` | Text |
| `purchase_timestamp` | Date/Time |
| `purchase_date` | Date |
| `purchase_year_month` | Text |
| `approval_timestamp` | Date/Time |
| `carrier_handoff_timestamp` | Date/Time |
| `delivery_timestamp` | Date/Time |
| `estimated_delivery_date` | Date |
| `approval_hours` | Decimal number |
| `preparation_days` | Decimal number |
| `transportation_days` | Decimal number |
| `total_lead_time_days` | Decimal number |
| `delivery_variance_days` | Whole number |
| `delay_days` | Whole number |
| `delivery_classification` | Text |
| `valid_approval_sequence` | Boolean, nullable |
| `valid_preparation_sequence` | Boolean, nullable |
| `valid_transportation_sequence` | Boolean, nullable |
| `valid_total_lead_time_sequence` | Boolean, nullable |
| `item_count` | Whole number |
| `seller_count` | Whole number |
| `category_count` | Whole number |
| `merchandise_value` | Decimal number |
| `freight_value` | Decimal number |
| `payment_record_count` | Whole number |
| `payment_value` | Decimal number |
| `review_count` | Whole number |
| `average_review_score` | Decimal number |
| `has_item_data` | Boolean |
| `has_review_data` | Boolean |

### `fact_order_items`

| Column | Power BI type |
| --- | --- |
| `order_id` | Text |
| `order_item_id` | Whole number |
| `product_id` | Text |
| `seller_id` | Text |
| `product_category_original` | Text |
| `product_category_english` | Text |
| `shipping_limit_timestamp` | Date/Time |
| `price` | Decimal number |
| `freight_value` | Decimal number |
| `customer_state` | Text |
| `seller_state` | Text |

### `dim_customers`

| Column | Power BI type |
| --- | --- |
| `customer_id` | Text |
| `customer_unique_id` | Text |
| `customer_city` | Text |
| `customer_state` | Text |
| `customer_zip_prefix` | Text |

### `dim_products`

| Column | Power BI type |
| --- | --- |
| `product_id` | Text |
| `product_category_original` | Text |
| `product_category_english` | Text |
| `product_name_lenght` | Whole number |
| `product_description_lenght` | Whole number |
| `product_photos_qty` | Whole number |
| `product_weight_g` | Whole number |
| `product_length_cm` | Whole number |
| `product_height_cm` | Whole number |
| `product_width_cm` | Whole number |

### `dim_sellers`

| Column | Power BI type |
| --- | --- |
| `seller_id` | Text |
| `seller_city` | Text |
| `seller_state` | Text |
| `seller_zip_prefix` | Text |

## Hidden columns

Hide relationship and technical keys from report view:

- `fact_orders[order_id]`, `fact_orders[customer_id]`
- `fact_order_items[order_id]`, `fact_order_items[product_id]`, `fact_order_items[seller_id]`
- `dim_customers[customer_id]`, `dim_products[product_id]`, `dim_sellers[seller_id]`

Also hide duplicated fact-side descriptive attributes to encourage use of the dimension fields:

- `fact_orders[customer_unique_id]`, `fact_orders[customer_city]`, `fact_orders[customer_state]`
- `fact_order_items[product_category_original]`, `fact_order_items[product_category_english]`
- `fact_order_items[customer_state]`, `fact_order_items[seller_state]`

Keep dimension descriptions visible. Keep `customer_unique_id` visible in `dim_customers` only if it is needed for the distinct-customer measure; otherwise it can also be hidden after the measure is created.

## Default summarization

Set **Do not summarize** for all IDs, `order_item_id`, ZIP prefixes, dates, timestamps, text fields, category fields, status/classification fields, and Boolean fields. This includes `delivery_variance_days` and `delay_days` when exposed as row-level attributes.

Use explicit measures for numeric aggregation. In particular, do not use implicit aggregation for `fact_orders[order_id]`, `fact_orders[customer_id]`, or `fact_order_items[order_item_id]`.

## Formatting

- Currency: `price` and `freight_value` in `fact_order_items`, plus `payment_value` in `fact_orders`; use the report currency with two decimal places. `fact_orders[merchandise_value]` and `fact_orders[freight_value]` are order-level aggregates retained for order analysis, not product/seller analysis.
- Percentage: `On-Time Delivery Rate` and `Late Delivery Rate`; use one decimal place or the report standard.
- Duration: `approval_hours` as `0.00` hours; day measures and duration measures as `0.00` days.
- Dates: `purchase_date` and `estimated_delivery_date` as date; timestamps as date/time.
- Scores: `Average Review Score` as `0.00`.
- Counts: whole numbers with thousands separators and zero decimal places.

## Final report pages and navigation

The final report has three pages. `Validation` is hidden from report consumers; `Overview` and `Product & Seller` are visible and are connected by a page navigator at the top of each visible page. The screenshots in `dashboard/screenshots/` are the visual record of this implementation.

### Overview page

Purpose: monitor order-volume, delivery, payment, and review performance at the order grain.

| Visual | Fields or measures |
| --- | --- |
| Customer State slicer | `dim_customers[customer_state]` |
| Date slicer | `DimDate[Date]` (Between) |
| KPI cards | `Average Lead Time Days`, `Total Orders`, `On-Time Delivery Rate`, `Total Payment Value`, `Average Review Score` |
| Delivery Classification donut | `fact_orders[delivery_classification]`, `Total Orders` |
| Monthly Order Volume and On-Time Rate combo chart | `DimDate[Year Month]`; `Total Orders`; `On-Time Delivery Rate` |
| Top 10 States by Late Orders bar chart | `dim_customers[customer_state]`; `Late Orders`; Top N = 10 |

Expected unfiltered KPI values are: Average Lead Time Days **12.56**, Total Orders **99,441**, On-Time Delivery Rate **93.23%**, Total Payment Value **R$16.01M** (exactly R$16,008,872.12), and Average Review Score **4.09**. The classification counts are 89,936 On Time, 6,534 Late, and 2,971 Not Classified.

### Product & Seller page

Purpose: compare merchandise, freight, and item activity at their native item grain by product category and seller state.

| Visual | Fields or measures |
| --- | --- |
| Product Category slicer | `dim_products[product_category_english]` |
| Seller State slicer | `dim_sellers[seller_state]` |
| Date slicer | `DimDate[Date]` (Between) |
| KPI cards | `Total Merchandise Value`, `Total Freight Value`, `Total Items` |
| Product Category Details matrix | `dim_products[product_category_english]`; `Total Items`, `Total Merchandise Value`, `Total Freight Value`, `Freight-to-Merchandise Ratio` |
| Top 10 Product Categories by Merchandise Value bar chart | `dim_products[product_category_english]`; `Total Merchandise Value`; Top N = 10 |
| Top 10 Seller States by Merchandise Value bar chart | `dim_sellers[seller_state]`; `Total Merchandise Value`; Top N = 10 |

Expected unfiltered KPI values are Total Merchandise Value **R$13.59M** (exactly R$13,591,643.70), Total Freight Value **R$2.25M** (exactly R$2,251,909.54), and Total Items **112,650**. The unfiltered `Freight-to-Merchandise Ratio` is **16.57%**.

### Hidden Validation page

Purpose: retain model-level check visuals during development without exposing them in normal report navigation. It is hidden. It is not a consumer-facing analytical page and should not be used as a substitute for running `python/03_power_bi_validation.py`.

## Filter propagation and analytical limitation

The Date slicer filters `DimDate`, then filters `fact_orders` through the active single-direction date relationship. Customer State filters `dim_customers` and then `fact_orders`; the approved one-to-one relationship uses Both because Power BI requires it. The active single-direction `fact_orders` to `fact_order_items` relationship carries date and customer/order filters to item measures. Product Category and Seller State filter only `fact_order_items` through their respective single-direction dimension relationships.

Consequently, product and seller analysis must use item-grain measures from `fact_order_items`. Do not place order-level delivery, payment, or review measures in product/seller analysis without an explicitly designed allocation or filtering method. Do not set product, seller, or order-item relationships to Both merely to make those measures respond: that changes the verified relationship design and risks ambiguous or misleading results.

## Nullable Boolean semantics

`valid_approval_sequence`, `valid_preparation_sequence`, `valid_transportation_sequence`, and `valid_total_lead_time_sequence` have three intentional states:

- `True`: both required timestamps exist and the sequence is valid.
- `False`: both required timestamps exist and the sequence is invalid.
- Blank/null: at least one required timestamp is missing.

Do not replace null with `False`. The complete `has_item_data` and `has_review_data` fields are ordinary two-state Booleans.

## Customer-table limitation

The current `dim_customers` table is keyed by order-level `customer_id`, so it has one row per order-level customer record and is one-to-one with `fact_orders` in the verified files. It is useful for customer attributes, but it is not a deduplicated real-customer dimension. Use `customer_unique_id` for cross-order distinct-customer and repeat-customer measures; do not use it as a relationship key.
