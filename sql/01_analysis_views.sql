-- Day 3 reusable SQLite views. Each view retains the grain stated below.

-- Grain: one row per order. No one-to-many detail table is joined here.
CREATE VIEW vw_order_analysis AS
SELECT
    order_id,
    customer_unique_id,
    customer_state,
    order_status,
    purchase_year_month,
    purchase_date,
    approval_timestamp,
    carrier_handoff_timestamp,
    delivery_timestamp,
    total_lead_time_days,
    delay_days,
    delivery_classification,
    valid_preparation_sequence,
    valid_transportation_sequence,
    payment_value
FROM fact_orders;

-- Grain: one row per order_id plus order_item_id. Only item-grain money is exposed.
CREATE VIEW vw_item_analysis AS
SELECT
    order_id,
    order_item_id,
    product_id,
    seller_id,
    COALESCE(product_category_english, 'Unknown') AS product_category,
    COALESCE(seller_state, 'Unknown') AS seller_state,
    price AS merchandise_value,
    freight_value
FROM fact_order_items;

-- Grain: one row per purchase year-month at the order grain.
CREATE VIEW vw_monthly_order_performance AS
SELECT
    purchase_year_month AS year_month,
    CASE
        WHEN purchase_year_month = (SELECT MIN(purchase_year_month) FROM vw_order_analysis)
          OR purchase_year_month = (SELECT MAX(purchase_year_month) FROM vw_order_analysis)
        THEN 1 ELSE 0
    END AS is_boundary_month,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN delivery_classification IN ('On Time', 'Late') THEN 1 ELSE 0 END) AS classified_orders,
    SUM(CASE WHEN delivery_classification = 'On Time' THEN 1 ELSE 0 END) AS on_time_orders,
    SUM(CASE WHEN delivery_classification = 'Late' THEN 1 ELSE 0 END) AS late_orders,
    1.0 * SUM(CASE WHEN delivery_classification = 'On Time' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN delivery_classification IN ('On Time', 'Late') THEN 1 ELSE 0 END), 0) AS on_time_rate,
    AVG(total_lead_time_days) AS average_total_lead_time_days,
    AVG(CASE WHEN delivery_classification = 'Late' THEN delay_days END) AS average_delay_days_late_orders
FROM vw_order_analysis
GROUP BY purchase_year_month;

-- Grain: one row per customer state at the order grain.
CREATE VIEW vw_customer_state_fulfillment AS
SELECT
    COALESCE(customer_state, 'Unknown') AS customer_state,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN delivery_classification IN ('On Time', 'Late') THEN 1 ELSE 0 END) AS classified_orders,
    SUM(CASE WHEN delivery_classification = 'Late' THEN 1 ELSE 0 END) AS late_orders,
    1.0 * SUM(CASE WHEN delivery_classification = 'On Time' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN delivery_classification IN ('On Time', 'Late') THEN 1 ELSE 0 END), 0) AS on_time_rate,
    AVG(total_lead_time_days) AS average_total_lead_time_days,
    AVG(CASE WHEN delivery_classification = 'Late' THEN delay_days END) AS average_delay_days_late_orders,
    SUM(payment_value) AS total_payment_value
FROM vw_order_analysis
GROUP BY COALESCE(customer_state, 'Unknown');

-- Grain: one row per resolved product category at the item grain.
CREATE VIEW vw_product_category_commercial AS
SELECT
    product_category,
    COUNT(*) AS total_items,
    SUM(merchandise_value) AS merchandise_value,
    SUM(freight_value) AS freight_value,
    1.0 * SUM(freight_value) / NULLIF(SUM(merchandise_value), 0) AS freight_to_merchandise_ratio
FROM vw_item_analysis
GROUP BY product_category;

-- Grain: one row per seller state at the item grain.
CREATE VIEW vw_seller_state_commercial AS
SELECT
    seller_state,
    COUNT(*) AS total_items,
    SUM(merchandise_value) AS merchandise_value,
    SUM(freight_value) AS freight_value,
    1.0 * SUM(freight_value) / NULLIF(SUM(merchandise_value), 0) AS freight_to_merchandise_ratio
FROM vw_item_analysis
GROUP BY seller_state;
