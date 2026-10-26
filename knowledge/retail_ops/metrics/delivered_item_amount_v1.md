---
doc_id: metric_delivered_item_amount
version: 1
title: 已交付订单商品金额 v1
doc_type: metric_contract
status: published
origin_type: project_defined
authority: project_metric_spec
published_at: 2026-10-25
effective_from: 2026-10-25
effective_to: null
business_domain: sales
metric_id: delivered_order_item_amount
---

# 已交付订单商品金额 v1

这是项目分析口径，金额单位 BRL。字段见[订单项](../schema/order_items.md)，公共约定见[数据范围说明](../overview/source_and_scope.md)。

## definition

按下单时间选择订单群，筛选 `order_status = 'delivered'`，对这些订单的订单项 `price` 求和。

该值是已交付订单的商品金额，**不含 `freight_value` 运费，不扣未知退款，不代表净成交额或利润**。`order_item_id` 是序号，不是数量，不能乘到价格上。

## 输入与粒度

必填统计起止时间和快照；当前默认版本 v1，默认全部客户州、全部商品类别和全部卖家。显式过滤条件必须在答案中列出。

金额按唯一订单项 `(order_id, order_item_id)` 累加。按客户州分析时通过订单和客户表关联；按类别、卖家分析时按订单项的归属计算，商品缺失类别显示 `UNKNOWN`，未翻译类别保留原名。

一个订单含两种类别时，各自只统计所属订单项金额，因此类别商品金额可以相加。但各类别“涉及订单数”会重复包含同一订单，不能相加作为总订单数。

## 缺失和异常

先报告期间订单数与已交付订单数，再报告无订单项的已交付订单数。不把缺失订单项解释为免费订单。

单项价格须能按十进制解析且非负；零金额保留。无效项不进入已知金额小计，报告数量并将输出标为部分结果；若存在缺失订单项的已交付订单，也标为部分结果。不要默默丢掉这些订单后宣称得到完整总额。

范围内没有已交付订单时，金额为 0，说明“无已交付订单”。有已交付订单但无任何有效订单项时，总额为 null，说明无法计算。存在部分有效项时可显示已知小计，但必须标为部分结果。

## 输出与关联

输出商品金额、有效订单项数、贡献金额的不同订单数、缺失订单项订单数和无效项数；金额展示两位小数。运费如需展示，单独标为运费，不混入本指标。

本指标不用支付表。需要同屏比较支付金额时，先分别按订单汇总，并明确两者状态范围是否一致；不能直接 JOIN 两张明细后求和。
