---
doc_id: schema_orders
version: 1
title: 订单与配送字段
doc_type: schema
status: published
origin_type: source_and_snapshot
authority: dataset_documentation
published_at: 2026-10-25
effective_from: 2026-10-25
effective_to: null
business_domain: orders
---

# 订单与配送字段

字段含义与本次快照检查结果；公共单位、时间与来源见[数据范围说明](../overview/source_and_scope.md)。

文件：`olist_orders_dataset.csv`，99,441 行，每行一笔订单。`order_id` 实测唯一。通过 `customer_id` 关联客户表，本次无失配。

| 字段 | 类型 | 含义／用途 | 空值数 |
| --- | --- | --- | ---: |
| `order_id` | 文本 | 订单唯一标识，用于关联订单项、支付和评价 | 0 |
| `customer_id` | 文本 | 关联客户表 `customers.customer_id`；跨订单识别同一客户需再取 `customer_unique_id` | 0 |
| `order_status` | 文本 | 数据快照中的订单状态，取值见下表 | 0 |
| `order_purchase_timestamp` | 日期时间 | 下单时间；按下单月份统计时使用 | 0 |
| `order_approved_at` | 日期时间 | 支付批准时间 | 160 |
| `order_delivered_carrier_date` | 日期时间 | 交给物流承运方的时间 | 1,783 |
| `order_delivered_customer_date` | 日期时间 | 实际交付客户的时间 | 2,965 |
| `order_estimated_delivery_date` | 日期时间 | 向客户提供的预计交付日期 | 0 |

原始下单时间范围：`2016-09-04 21:15:19` 至 `2018-10-17 17:30:18`。这只是最早与最晚记录，不表示首尾月份都有完整数据。

| 状态值 | 中文说明 | 订单数 |
| --- | --- | ---: |
| `delivered` | 已交付 | 96,478 |
| `shipped` | 已发货／运输中 | 1,107 |
| `canceled` | 已取消 | 625 |
| `unavailable` | 无法供货／不可用 | 609 |
| `invoiced` | 已开票 | 314 |
| `processing` | 处理中 | 301 |
| `created` | 已创建 | 5 |
| `approved` | 已批准 | 2 |

使用约定：

- 下单时间、支付批准时间、交运时间、交付时间各自表达不同事件，查询时按指标口径选择。
- 时间字符串没有时区偏移，本阶段保留原始日历值，不做时区转换；原始空字符串导入数据库时转为 NULL。
- 延迟率需要实际和预计交付日期；缺失实际交付时间不能当成准时。“同一天是否算延迟”和分母范围由指标契约规定。
- `canceled` 只表示取消；这三张表没有退款事件或退款成功金额。
