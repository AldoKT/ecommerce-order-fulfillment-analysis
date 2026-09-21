-- Day 3 SQLite business queries. Each label is executed by python/04_sql_analysis.py.

-- QUERY: overall_order_fulfillment_summary
-- Grain: all orders, one summary row.
SELECT
    COUNT(*) AS total_orders,
    SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
    SUM(CASE WHEN delivery_classification IN ('On Time', 'Late') THEN 1 ELSE 0 END) AS classified_orders,
    SUM(CASE WHEN delivery_classification = 'On Time' THEN 1 ELSE 0 END) AS on_time_orders,
    SUM(CASE WHEN delivery_classification = 'Late' THEN 1 ELSE 0 END) AS late_orders,
    1.0 * SUM(CASE WHEN delivery_classification = 'On Time' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN delivery_classification IN ('On Time', 'Late') THEN 1 ELSE 0 END), 0) AS on_time_rate,
    AVG(total_lead_time_days) AS average_total_lead_time_days,
    AVG(CASE WHEN delivery_classification = 'Late' THEN delay_days END) AS average_delay_days_late_orders
FROM vw_order_analysis;

-- QUERY: monthly_fulfillment_trend
-- Grain: purchase year-month at order grain.
SELECT
    year_month,
    is_boundary_month,
    total_orders,
    classified_orders,
    late_orders,
    on_time_rate,
    average_total_lead_time_days,
    average_delay_days_late_orders
FROM vw_monthly_order_performance
ORDER BY year_month;

-- QUERY: customer_state_fulfillment_performance
-- Grain: customer state at order grain. Compare rates only where at least 100 orders are classified.
SELECT
    customer_state,
    total_orders,
    classified_orders,
    late_orders,
    on_time_rate,
    average_total_lead_time_days,
    average_delay_days_late_orders,
    total_payment_value
FROM vw_customer_state_fulfillment
WHERE classified_orders >= 100
ORDER BY on_time_rate ASC, classified_orders DESC, customer_state;

-- QUERY: order_status_distribution
-- Grain: order status. Division is protected when the order table is empty.
SELECT
    order_status,
    COUNT(*) AS order_count,
    1.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM vw_order_analysis), 0) AS percentage_of_all_orders
FROM vw_order_analysis
GROUP BY order_status
ORDER BY order_count DESC, order_status;

-- QUERY: product_category_commercial_performance
-- Grain: product category at item grain. No order-level delivery, payment, or review metric is used.
SELECT
    product_category,
    total_items,
    merchandise_value,
    freight_value,
    freight_to_merchandise_ratio
FROM vw_product_category_commercial
ORDER BY merchandise_value DESC, product_category;

-- QUERY: seller_state_commercial_performance
-- Grain: seller state at item grain. No order-level delivery, payment, or review metric is used.
SELECT
    seller_state,
    total_items,
    merchandise_value,
    freight_value,
    freight_to_merchandise_ratio
FROM vw_seller_state_commercial
ORDER BY merchandise_value DESC, seller_state;

-- QUERY: customer_repeat_order_summary
-- Grain: one summary row; individual customer identifiers are intentionally not returned.
WITH customer_order_counts AS (
    SELECT customer_unique_id, COUNT(*) AS order_count
    FROM vw_order_analysis
    WHERE customer_unique_id IS NOT NULL
    GROUP BY customer_unique_id
), customer_summary AS (
    SELECT
        COUNT(*) AS distinct_customers,
        SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END) AS one_time_customers,
        SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers,
        MAX(order_count) AS maximum_orders_by_one_customer
    FROM customer_order_counts
)
SELECT
    distinct_customers,
    one_time_customers,
    repeat_customers,
    1.0 * repeat_customers / NULLIF(distinct_customers, 0) AS repeat_customer_rate,
    maximum_orders_by_one_customer
FROM customer_summary;

-- QUERY: data_quality_and_lifecycle_summary
-- Grain: all orders, one summary row. Counts are diagnostic, not exclusions.
SELECT
    SUM(CASE WHEN approval_timestamp IS NULL THEN 1 ELSE 0 END) AS missing_approval_timestamps,
    SUM(CASE WHEN carrier_handoff_timestamp IS NULL THEN 1 ELSE 0 END) AS missing_carrier_handoff_timestamps,
    SUM(CASE WHEN delivery_timestamp IS NULL THEN 1 ELSE 0 END) AS missing_delivery_timestamps,
    SUM(CASE WHEN approval_timestamp IS NULL OR carrier_handoff_timestamp IS NULL OR delivery_timestamp IS NULL THEN 1 ELSE 0 END) AS orders_missing_any_lifecycle_timestamp,
    SUM(CASE WHEN valid_preparation_sequence = 0 THEN 1 ELSE 0 END) AS invalid_preparation_sequences,
    SUM(CASE WHEN valid_transportation_sequence = 0 THEN 1 ELSE 0 END) AS invalid_transportation_sequences,
    SUM(CASE WHEN delivery_classification = 'Not Classified' THEN 1 ELSE 0 END) AS not_classified_orders
FROM vw_order_analysis;
