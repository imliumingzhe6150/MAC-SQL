---
doc_id: schema_order_payments
version: 1
title: 支付记录、方式与分期字段
doc_type: schema
status: published
origin_type: source_and_snapshot
authority: dataset_documentation
published_at: 2026-10-25
effective_from: 2026-10-25
effective_to: null
business_domain: payments
---

# 支付记录、方式与分期字段

字段含义与本次快照检查结果；公共单位、时间与来源见[数据范围说明](../overview/source_and_scope.md)。

文件：`olist_order_payments_dataset.csv`，103,886 行，每行一条支付记录。组合键 `(order_id, payment_sequential)` 实测唯一；订单引用均有效，但订单表有 1 笔订单没有支付记录。

| 字段 | 类型 | 含义／用途 |
| --- | --- | --- |
| `order_id` | 文本 | 所属订单，关联 `orders.order_id` |
| `payment_sequential` | 整数 | 订单内的支付记录序号，不是分期期数 |
| `payment_type` | 文本 | 支付方式，取值见下表 |
| `payment_installments` | 整数 | 分期期数；不能再乘到 `payment_value` 上 |
| `payment_value` | 金额 | 该支付记录的金额，单位 BRL |

| 支付方式 | 中文说明 | 支付记录数 |
| --- | --- | ---: |
| `credit_card` | 信用卡 | 76,795 |
| `boleto` | 巴西付款单支付 | 19,784 |
| `voucher` | 代金券 | 5,775 |
| `debit_card` | 借记卡 | 1,529 |
| `not_defined` | 未定义 | 3 |

这张表本次检查所有字段均无空值，覆盖 99,440 笔订单，其中 2,961 笔有多个支付记录。`payment_installments` 实际范围为 0～24，其中 2 条记录为 0；计算分期分布时单独列出，不自行改成 1。

计算订单支付记录总额时，按 `order_id` 对 `payment_value` 求和。这里没有逐笔到账日期，不能用它直接制作按到账日统计的现金流水。


金额统计见[支付记录金额契约](../metrics/payment_record_amount_v1.md)。分期数为 2 不意味着存在两条付款流水，支付方式记录数也不是独立订单数。
