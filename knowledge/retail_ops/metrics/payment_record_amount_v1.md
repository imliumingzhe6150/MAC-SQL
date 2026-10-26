---
doc_id: metric_payment_record_amount
version: 1
title: 按下单订单群计算的支付记录金额 v1
doc_type: metric_contract
status: published
origin_type: project_defined
authority: project_metric_spec
published_at: 2026-10-25
effective_from: 2026-10-25
effective_to: null
business_domain: payments
metric_id: payment_record_amount_by_purchase_cohort
---

# 按下单订单群计算的支付记录金额 v1

这是项目分析口径。字段见[支付说明](../schema/order_payments.md)，公共约定见[数据范围说明](../overview/source_and_scope.md)。

## definition

选择下单时间在 `[period_start, period_end)` 的订单，对关联支付记录的 `payment_value` 求和，单位 BRL。默认包含所有订单状态，包括 canceled；这里统计快照记录，不把订单状态当作资金结算证明。

指标不是到账收入、扣退款净额，也不是按支付发生日期统计的流水。`order_approved_at` 不能替代每条支付记录的到账时间。

## 参数与统计范围

记录起止时间、`db_snapshot`、`metric_version=1`。默认全部客户州、全部支付方式、全部订单状态；可显式指定状态或支付方式，输出必须显示过滤条件。例如与已交付商品金额比较时，可指定 `order_status = 'delivered'`，但不能静默修改默认范围。

每条支付记录按组合键 `(order_id, payment_sequential)` 计一次。`payment_installments` 不参与金额乘算。按支付方式分组时，各方式金额可相加；同一订单用两种方式支付，会同时出现在两个分组的不同订单数中，分组订单数不可直接相加。

## 缺失与异常

金额须为可解析非负十进制值，零金额保留。无效记录计数并排除，金额标为已知小计/部分结果。符合范围但没有任何支付记录的订单单独计数，不能解释为未付款或支付金额为零。

如果指定支付方式，一笔订单有支付记录但没有该方式，是不匹配过滤条件，不是缺失数据；缺失支付记录计数基于支付方式过滤前的订单群。

订单群为空时输出 0 并说明无订单。订单群非空、完整记录中没有匹配支付方式时输出 0 并说明无匹配记录。有订单但支付记录全部缺失/无效时输出 null；部分缺失时返回已知小计并标记部分结果。

## 输出

返回订单群数量、匹配支付记录数、匹配的不同订单数、支付记录金额、缺失记录订单数、无效金额记录数及范围说明。金额显示两位小数，计算用十进制或整数分。

本指标不需要订单项表。首版不把整笔订单的支付记录金额按商品类别或卖家分摊；需要类别金额时使用[商品金额契约](delivered_item_amount_v1.md)。
