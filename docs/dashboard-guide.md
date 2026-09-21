# Day 2 dashboard guide

## Overview

The **Overview** page is the order-grain operating view. It contains a Customer State slicer (`dim_customers[customer_state]`) and a Between Date slicer (`DimDate[Date]`), KPI cards for `Average Lead Time Days`, `Total Orders`, `On-Time Delivery Rate`, `Total Payment Value`, and `Average Review Score`, a Delivery Classification donut, a monthly order-volume and on-time-rate combo chart, and a Top 10 States by Late Orders bar chart. The page navigator provides access to the Product & Seller page.

With no filters, the KPI cards should show 12.56 average lead-time days, 99,441 total orders, 93.23% on-time delivery rate, R$16.01M total payment value (R$16,008,872.12), and 4.09 average review score. The delivery donut should reconcile to 89,936 On Time, 6,534 Late, and 2,971 Not Classified orders.

## Product & Seller

The **Product & Seller** page is the item-grain commercial view. It contains Product Category (`dim_products[product_category_english]`), Seller State (`dim_sellers[seller_state]`), and Between Date (`DimDate[Date]`) slicers; KPI cards for `Total Merchandise Value`, `Total Freight Value`, and `Total Items`; a Product Category Details matrix using `Total Items`, `Total Merchandise Value`, `Total Freight Value`, and `Freight-to-Merchandise Ratio`; and Top 10 bar charts for product categories and seller states by `Total Merchandise Value`.

With no filters, the KPI cards should show R$13,591,643.70 merchandise, R$2,251,909.54 freight, and 112,650 items. The matrix total freight-to-merchandise ratio should show 16.57%.

## Validation

The **Validation** page is hidden. It is reserved for development checks and is excluded from normal page navigation. The executable, source-controlled validation is `python/03_power_bi_validation.py`.

## Filter behavior and limitations

Date and Customer State filters reach `fact_orders`, and the active single-direction order-to-item relationship then filters item measures. Product Category and Seller State filters flow only from their dimensions to `fact_order_items`. This makes item measures responsive on the Product & Seller page.

Delivery, payment, and review measures are order-grain measures. They must not be interpreted by product or seller unless an explicit allocation or filtering method is designed and documented. Do not change relationships to bidirectional simply to make those measures react to product or seller filters.
