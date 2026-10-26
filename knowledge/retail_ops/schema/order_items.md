---
doc_id: schema_order_items
version: 1
title: 订单项、商品金额与运费字段
doc_type: schema
status: published
origin_type: source_and_snapshot
authority: dataset_documentation
published_at: 2026-10-25
effective_from: 2026-10-25
effective_to: null
business_domain: sales
---

# 订单项、商品金额与运费字段

字段含义与本次快照检查结果；公共单位、时间与来源见[数据范围说明](../overview/source_and_scope.md)。

文件：`olist_order_items_dataset.csv`，112,650 行，每行一个订单项。组合键 `(order_id, order_item_id)` 实测唯一，订单、商品、卖家引用均可找到对应记录；订单表中 775 笔订单没有订单项。

| 字段 | 类型 | 含义／用途 |
| --- | --- | --- |
| `order_id` | 文本 | 所属订单，关联 `orders.order_id` |
| `order_item_id` | 整数 | 订单内的订单项序号；不是商品 ID，也不是购买数量 |
| `product_id` | 文本 | 商品 ID，关联商品表 |
| `seller_id` | 文本 | 该订单项的卖家 ID，关联卖家表 |
| `shipping_limit_date` | 日期时间 | 卖家将该订单项交给物流方的截止时间；不是客户预计收货时间 |
| `price` | 金额 | 该订单项的商品金额，单位 BRL（巴西雷亚尔） |
| `freight_value` | 金额 | 分配到该订单项的运费，单位 BRL |

这张表本次检查所有字段均无空值，覆盖 98,666 笔订单，其中 9,803 笔有多个订单项。

计算某笔订单的商品金额时，对该订单的 `price` 求和；运费对 `freight_value` 求和。表中没有单独的 `quantity` 列，不要把 `order_item_id` 当数量乘到价格上。同一订单可以包含不同商品和卖家。


金额统计见[已交付订单商品金额契约](../metrics/delivered_item_amount_v1.md)。先按订单或目标维度汇总订单项，再关联其他明细表。
