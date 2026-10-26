---
doc_id: metric_delivered_order_late_rate
version: 1
title: 按下单订单群计算的已交付订单延迟率
doc_type: metric_contract
status: published
origin_type: project_defined
authority: project_metric_spec
published_at: 2026-10-25
effective_from: 2026-10-25
effective_to: null
business_domain: delivery
metric_id: delivered_order_late_rate
---

# 已交付订单延迟率 v1

这是本项目制定的分析口径，用于 Olist 历史数据，不代表 Olist 官方 KPI。v1 从 2026-10-25 起作为项目口径使用，可以用于分析数据集中更早的订单。

## definition

**延迟率 = 延迟交付订单数 ÷ 有效已交付订单数。** 每笔订单计一次。

先按 `orders.order_purchase_timestamp` 选择下单期间，再从中筛选有效已交付订单。这个指标回答的是“这批下单订单中，最终已交付且有有效日期的订单，有多少延迟”，不是“当月交付的所有订单有多少延迟”。

有效已交付订单须同时满足：

1. 快照中的 `order_status = 'delivered'`。
2. 下单时间、实际交付时间 `order_delivered_customer_date`、预计交付时间 `order_estimated_delivery_date` 均非空且可解析。
3. 实际交付时间和预计交付时间均不早于下单时间；此项按完整时间比较。

在上述订单中，**实际交付的日历日期 > 预计交付的日历日期**即为延迟。实际与预计在同一天时不算延迟，不比较当天几点。

例如预计 1 月 10 日、实际 1 月 10 日 18:00 交付，不算延迟；实际 1 月 11 日交付则算延迟。

## 查询参数与时间

| 参数 | 约定 |
| --- | --- |
| `period_start`、`period_end` | 必填，下单期间为左闭右开区间 `[start, end)`；2018 年 1 月即 `[2018-01-01, 2018-02-01)` |
| `customer_state_scope` | 可指定客户州；不指定默认全部客户州，回答时显示范围 |
| `metric_version` | 当前默认 v1，用户显式指定其他版本时须找到对应契约 |
| `db_snapshot` | 必须记录实际使用的数据快照，不能默认为实时数据 |

原始日期时间按源文件日历值解析，不做时区换算。缺少统计期间时询问用户；“本月”等相对当前时间的请求若不在历史数据覆盖范围内，说明无覆盖，不自动改成数据集最后一个月。

统计期只限制下单时间：1 月下单、2 月交付的有效订单仍属于 1 月订单群。是否延迟使用固定快照中的交付结果，不要求在统计期结束前交付。原始数据的业务观察截止时点未知，`data_as_of` 记为 null；下载日期不作为该时点。

## 客户州与关联

用 `orders.customer_id = customers.customer_id` 关联，按 `customers.customer_state` 分组。卖家州不用于本指标。

客户表的 `customer_id` 应唯一，确保每笔订单只出现一次。客户关联缺失或州为空时，归为 `UNKNOWN`，全部客户州统计包含该组；指定州统计只包含所选州。计算本指标不需要关联订单项、支付或评价表。

## 排除与输出

对所选期间和客户州范围内的订单，按下面顺序记录一个排除原因，避免重复计数：

1. 状态不是 `delivered`：`not_delivered`。
2. 实际或预计交付时间缺失/无法解析：`invalid_delivery_time`。
3. 实际或预计交付时间早于下单时间：`invalid_time_order`。

下单时间缺失/无法解析的订单无法归入期间，另报全局数量 `unassigned_purchase_time_count`，不硬塞进某月排除数。

| 输出 | 含义 |
| --- | --- |
| `cohort_order_count` | 所选期间与客户州范围内的全部订单数 |
| `eligible_order_count` | 有效已交付订单数，分母 |
| `late_order_count` | 有效订单中的延迟订单数，分子 |
| `excluded_order_count` | 订单群数量减去有效订单数，附排除原因计数 |
| `late_rate` | 未舍入比例，范围 0～1；分母为零则为 null |

展示百分比保留两位小数，采用四舍五入（ROUND_HALF_UP）。分母为零显示“无有效已交付订单，无法计算”，不能显示 0%。期间没有订单时说明“该范围无订单”，不把空结果当查询失败。

参考结果核对时，订单计数必须完全一致；未舍入比例的绝对误差容差为 `1e-12`。展示值由原始计数直接计算，不能用已舍入的各州百分比求总体平均值；总体延迟率用分子合计除以分母合计。

## 依据

- 字段与关联说明：[数据字典](../../../data/retail_ops/DATA_DICTIONARY.md)。
- 数据来源：[Olist 官方公开数据集](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)，本地快照见[下载清单](../../../data/retail_ops/download_manifest.json)。
- 本文的分母、日期判断、排除顺序、缺失州处理和舍入方式均为项目约定。实际运行结果和参考 SQL 存放在 `evals/retail_ops/`，不作为知识文档内容。
