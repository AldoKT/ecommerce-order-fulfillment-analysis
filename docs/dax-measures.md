# Day 2 DAX measures

These measures assume the table and column names from `docs/power-bi-model-spec.md`. Create them as explicit measures; do not rely on implicit aggregations.

## Date table

Create this calculated table before creating the date relationship:

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

Mark `DimDate` as the date table using `DimDate[Date]`. Create an active one-to-many relationship from `DimDate[Date]` to `fact_orders[purchase_date]` with Single cross-filter direction from `DimDate` to `fact_orders`. Sort `Month Name` by `Month Number` and `Year Month` by `Year Month Sort`.

## Order measures

```DAX
Total Orders =
COUNTROWS ( fact_orders )
```

```DAX
Delivered Orders =
CALCULATE (
    [Total Orders],
    fact_orders[order_status] = "delivered"
)
```

```DAX
Classified Orders =
CALCULATE (
    [Total Orders],
    fact_orders[delivery_classification] IN { "On Time", "Late" }
)
```

```DAX
On-Time Orders =
CALCULATE (
    [Total Orders],
    fact_orders[delivery_classification] = "On Time"
)
```

```DAX
Late Orders =
CALCULATE (
    [Total Orders],
    fact_orders[delivery_classification] = "Late"
)
```

`Classified Orders` is the denominator for delivery-rate measures, so `Not Classified` orders are excluded.

```DAX
On-Time Delivery Rate =
DIVIDE ( [On-Time Orders], [Classified Orders] )
```

```DAX
Late Delivery Rate =
DIVIDE ( [Late Orders], [Classified Orders] )
```

```DAX
Average Lead Time Days =
AVERAGE ( fact_orders[total_lead_time_days] )
```

```DAX
Average Delay Days for Late Orders =
CALCULATE (
    AVERAGE ( fact_orders[delay_days] ),
    fact_orders[delivery_classification] = "Late"
)
```

The lead-time measure averages valid nonblank durations. The delay measure explicitly filters to late orders; `delay_days` is already blank for on-time and unclassified orders.

## Monetary measures

```DAX
Total Merchandise Value =
SUM ( fact_order_items[price] )
```

```DAX
Total Freight Value =
SUM ( fact_order_items[freight_value] )
```

```DAX
Freight-to-Merchandise Ratio =
DIVIDE (
    [Total Freight Value],
    [Total Merchandise Value]
)
```

```DAX
Total Payment Value =
SUM ( fact_orders[payment_value] )
```

Merchandise and freight are calculated from the item-grain fact so product and seller filters affect them. The similarly named `fact_orders[merchandise_value]` and `fact_orders[freight_value]` columns are order-level aggregates and should not be used for product or seller analysis. Payment remains an order-level measure because it uses `fact_orders[payment_value]`.

With no report filters, `Freight-to-Merchandise Ratio` is approximately **16.57%** (`2,251,909.54 / 13,591,643.70`). Format it as a percentage with two decimal places.

## Review and item measures

```DAX
Average Review Score =
AVERAGE ( fact_orders[average_review_score] )
```

```DAX
Total Items =
COUNTROWS ( fact_order_items )
```

`Total Items` counts rows at the native item grain; it does not sum `order_item_id`, which is a sequence number rather than a quantity.

`Average Review Score` is an order-weighted average of the order-level `average_review_score` values. It is not a review-row-weighted average because review detail is not present in the processed model.

## Grain limitation for product and seller analysis

Product and seller visuals must use item-grain measures from `fact_order_items`, such as `Total Merchandise Value`, `Total Freight Value`, `Freight-to-Merchandise Ratio`, and `Total Items`. Do not use order-level delivery, payment, or review measures by product or seller unless an explicit allocation or filtering method has been designed and documented. The model relationships must not be changed to bidirectional merely to make those order-level measures react to product or seller filters; doing so would change filter semantics and can create ambiguous or misleading results.

## Customer measures

```DAX
Distinct Customers =
DISTINCTCOUNT ( dim_customers[customer_unique_id] )
```

```DAX
Repeat Customers =
COUNTROWS (
    FILTER (
        VALUES ( dim_customers[customer_unique_id] ),
        CALCULATE ( DISTINCTCOUNT ( fact_orders[order_id] ) ) > 1
    )
)
```

The customer measures use `customer_unique_id` for cross-order identity. The approved one-to-one customer relationship allows dimension filters to reach orders, but the identifier itself remains unsuitable as a relationship key.

## Recommended display formats

| Measure group | Format |
| --- | --- |
| Order, item, and customer counts | Whole number with thousands separator |
| `On-Time Delivery Rate`, `Late Delivery Rate` | Percentage, one decimal place |
| `Freight-to-Merchandise Ratio` | Percentage, two decimal places |
| Monetary measures | Currency, two decimal places |
| `Average Lead Time Days`, `Average Delay Days for Late Orders` | Decimal number, two decimal places |
| `Average Review Score` | Decimal number, two decimal places |
