# Day 3 SQL business analysis

This report is generated deterministically by `python/04_sql_analysis.py`; it contains no execution timestamp.

## Scope and analytical assumptions

The analysis uses the processed order and order-item facts only. Delivery, payment, and review metrics remain at order grain. Product-category and seller-state commercial metrics use only item-grain price and freight values; merchandise value is revenue-like transaction value, not profit.

## Source tables and grain

| Source | Grain | Use |
| --- | --- | --- |
| `fact_orders.csv` | One row per order | fulfillment, status, payment, lifecycle, repeat-order summaries |
| `fact_order_items.csv` | One row per `order_id` + `order_item_id` | product-category and seller-state commercial summaries |

## Method

The runner loads the two processed facts into an in-memory SQLite database using explicit practical column types, creates reusable views, executes all named queries, and reconciles results to the processed CSV source rows. No database file is created. All rate divisions use `NULLIF` to return null rather than raise or misstate a value when a denominator is zero.

## Headline KPI results

| Total orders | Delivered | Classified | On time | Late | On-time rate | Avg. lead time (days) | Avg. late delay (days) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 99,441 | 96,478 | 96,470 | 89,936 | 6,534 | 93.23% | 12.56 | 10.62 |

## Monthly fulfillment findings

Boundary months are **2016-09, 2018-10**. They remain in the monthly SQL output for transparency but are flagged as partial boundary months and excluded from comparative rankings.

Observed fact: the following are the five purchase months with the lowest on-time rate among non-boundary months having at least 100 classified orders.

| Year month | Orders | Classified | Late | On-time rate | Avg. lead time (days) | Avg. late delay (days) |
| --- | --- | --- | --- | --- | --- | --- |
| 2018-03 | 7,211 | 7,003 | 1,328 | 81.04% | 16.30 | 10.02 |
| 2018-02 | 6,728 | 6,555 | 926 | 85.87% | 16.95 | 12.58 |
| 2017-11 | 7,544 | 7,288 | 904 | 87.60% | 15.16 | 11.18 |
| 2017-12 | 5,673 | 5,513 | 411 | 92.54% | 15.39 | 9.73 |
| 2018-05 | 6,873 | 6,749 | 443 | 93.44% | 11.42 | 7.10 |

## Customer-state analysis

Observed fact: rate comparisons below apply the pre-defined minimum-volume rule of at least 100 classified orders.

| Customer state | Orders | Classified | Late | On-time rate | Avg. lead time (days) | Avg. late delay (days) | Payment value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AL | 413 | 397 | 85 | 78.59% | 24.54 | 9.54 | R$96,962.06 |
| MA | 747 | 717 | 125 | 82.57% | 21.57 | 10.50 | R$152,523.02 |
| SE | 350 | 335 | 51 | 84.78% | 21.52 | 16.20 | R$75,246.25 |
| PI | 495 | 476 | 66 | 86.13% | 19.46 | 13.35 | R$108,523.97 |
| CE | 1,336 | 1,279 | 176 | 86.24% | 21.27 | 15.18 | R$279,464.03 |
| BA | 3,380 | 3,256 | 396 | 87.84% | 19.34 | 12.02 | R$616,645.82 |
| RJ | 12,852 | 12,350 | 1,495 | 87.89% | 15.31 | 13.52 | R$2,144,379.69 |
| PA | 975 | 946 | 106 | 88.79% | 23.77 | 12.82 | R$218,295.85 |
| ES | 2,033 | 1,995 | 214 | 89.27% | 15.79 | 11.30 | R$325,967.55 |
| PB | 536 | 517 | 54 | 89.56% | 20.43 | 10.33 | R$141,545.72 |

## Order-status analysis

| Order status | Orders | Share of orders |
| --- | --- | --- |
| delivered | 96,478 | 97.02% |
| shipped | 1,107 | 1.11% |
| canceled | 625 | 0.63% |
| unavailable | 609 | 0.61% |
| invoiced | 314 | 0.32% |
| processing | 301 | 0.30% |
| created | 5 | 0.01% |
| approved | 2 | 0.00% |

## Product-category analysis

Observed fact: the table ranks categories by item-grain merchandise value. It does not attach delivery, payment, or review outcomes to categories.

| Product category | Items | Merchandise value | Freight value | Freight / merchandise |
| --- | --- | --- | --- | --- |
| health_beauty | 9,670 | R$1,258,681.34 | R$182,566.73 | 14.50% |
| watches_gifts | 5,991 | R$1,205,005.68 | R$100,535.93 | 8.34% |
| bed_bath_table | 11,115 | R$1,036,988.68 | R$204,693.04 | 19.74% |
| sports_leisure | 8,641 | R$988,048.97 | R$168,607.51 | 17.06% |
| computers_accessories | 7,827 | R$911,954.32 | R$147,318.08 | 16.15% |
| furniture_decor | 8,334 | R$729,762.49 | R$172,749.30 | 23.67% |
| cool_stuff | 3,796 | R$635,290.85 | R$84,039.10 | 13.23% |
| housewares | 6,964 | R$632,248.66 | R$146,149.11 | 23.12% |
| auto | 4,235 | R$592,720.11 | R$92,664.21 | 15.63% |
| garden_tools | 4,347 | R$485,256.46 | R$98,962.75 | 20.39% |

## Seller-state analysis

Observed fact: the table ranks seller states by item-grain merchandise value. It does not attach delivery, payment, or review outcomes to seller states.

| Seller state | Items | Merchandise value | Freight value | Freight / merchandise |
| --- | --- | --- | --- | --- |
| SP | 80,342 | R$8,753,396.21 | R$1,482,487.67 | 16.94% |
| PR | 8,671 | R$1,261,887.21 | R$197,013.52 | 15.61% |
| MG | 8,827 | R$1,011,564.74 | R$212,595.06 | 21.02% |
| RJ | 4,818 | R$843,984.22 | R$93,829.90 | 11.12% |
| SC | 4,075 | R$632,426.07 | R$106,547.06 | 16.85% |
| RS | 2,199 | R$378,559.54 | R$57,243.09 | 15.12% |
| BA | 643 | R$285,561.56 | R$19,700.68 | 6.90% |
| DF | 899 | R$97,749.48 | R$18,494.06 | 18.92% |
| PE | 448 | R$91,493.85 | R$12,392.46 | 13.54% |
| GO | 520 | R$66,399.21 | R$12,565.50 | 18.92% |

## Repeat-customer summary

| Distinct customers | One-time customers | Repeat customers | Repeat-customer rate | Maximum orders by one customer |
| --- | --- | --- | --- | --- |
| 96,096 | 93,099 | 2,997 | 3.12% | 17 |

## Data-quality caveats

| Missing approval | Missing carrier handoff | Missing delivery | Missing any lifecycle timestamp | Invalid preparation | Invalid transportation | Not classified |
| --- | --- | --- | --- | --- | --- | --- |
| 160 | 1,783 | 2,965 | 2,980 | 1,359 | 23 | 2,971 |

Lifecycle averages use non-null valid durations created in Day 1. Not Classified orders are excluded from on-time rate denominators; diagnostic counts are retained rather than corrected or removed.

## Business interpretation

Observed fact: 6,534 of 96,470 classified orders are late, while 2,971 orders are Not Classified.

Interpretation: delivery performance varies by time period and customer state in this observational dataset. These associations do not establish why delays occurred.

Recommendation: use the lowest on-time-rate months and qualifying customer states as a prioritization list for operational investigation, then validate any proposed causes with process-level evidence before changing policy.

## Limitations

- The dataset is observational and anonymized; it cannot establish causation or operational accountability.
- `customer_unique_id` is used only in aggregated repeat-order calculations; no individual customer identifiers are reported.
- Payment, delivery, and review measures must not be analyzed by product category or seller state without a separately designed valid allocation method.
- Merchandise value is not profit and does not account for costs, refunds, or margin.
- Missing lifecycle timestamps and retained invalid sequences limit delivery-duration coverage.

## Reproducibility command

```powershell
& .\.venv\Scripts\python.exe python\04_sql_analysis.py
```
