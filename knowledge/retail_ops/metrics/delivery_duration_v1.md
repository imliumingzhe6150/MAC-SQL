---
doc_id: metric_delivery_duration
version: 1
title: 下单至交付平均时长 v1
doc_type: metric_contract
status: published
origin_type: project_defined
authority: project_metric_spec
published_at: 2026-10-25
effective_from: 2026-10-25
effective_to: null
business_domain: delivery
metric_id: order_to_delivery_mean_days
---

# 下单至交付平均时长 v1

这是项目分析口径。公共时间、快照和地区约定见[数据范围说明](../overview/source_and_scope.md)，字段见[订单与配送](../schema/orders.md)。

## definition

每笔有效订单的配送时长（天） = `(实际交付时间 - 下单时间)` 的总秒数 ÷ 86,400。

平均配送时长 = 有效订单时长之和 ÷ 有效订单数。每笔订单权重相同。这里统计从下单到交付的完整耗时，包括处理与运输，不是“交运到交付”的纯运输时长。

## 订单范围与排除

按下单时间选择 `[period_start, period_end)`，仅包含快照状态 `delivered` 的订单，默认所有客户州。下单时间及实际交付时间须可解析，实际交付不得早于下单。

预计交付时间不参与本指标，因此预计日期缺失的订单仍可参与配送时长，但可能被延迟率排除。两项指标有效样本量不必相同。跨月交付仍计入原下单月份，不要求交付发生在统计期内。

无法归期的下单时间另计；已归期订单依次按非已交付、交付时间缺失/非法、交付早于下单三个原因排除。

## 计算与输出

使用完整时间差，不用两个日历日期相减。例如下单 1 月 1 日 18:00、交付 1 月 2 日 06:00，时长为 0.5 天。

输出订单群数量、有效订单数、排除数及原因、时长总秒数、平均天数。展示平均天数两位小数（ROUND_HALF_UP），计算时保留未舍入值。零有效订单返回 null 并说明不可计算。

客户州通过客户表关联；不需要订单项或支付表。比较州时同时展示样本数，不把长时长直接解释为卖家或承运方责任。

## 必需参数与边界

记录 `period_start`、`period_end`、`customer_state_scope`（默认全部）、`metric_version=1`、`db_snapshot`。用户说“运输时长”时询问是下单到交付还是交运到交付；本契约只定义前者。
