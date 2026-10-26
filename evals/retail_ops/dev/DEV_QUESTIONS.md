# Olist 第一批开发题（20 道）

修订：2026-10-26。17 道采用日常问法，3 道保留版本与时间专项检查。题目不直接训练模型，用于调整与检验检索、路由和回答。

基于现有 12 份 v1 文档；数值题使用完整 Olist v2 固定快照。本文含答案，不作为模型输入或检索语料。

构成：6 道单文档、4 道跨文档、3 道版本与时间、4 道联合查数、3 道边界题。数值参考经过 SQL 与独立 Python 核对，尚未运行 RAG 评测。

## dev001 · 单文档

说好 1 月 10 日送到，结果当天晚上 8 点才到，这算晚到吗？不用查具体订单。

预期：`knowledge` → `answered`。

**答案要点**

- 在满足有效订单条件的前提下不算延迟
- v1 比较日历日期，同一天不算延迟，不比较当天具体时间

**依据**

- [metric_delivered_order_late_rate v1](../../../knowledge/retail_ops/metrics/delivered_order_late_rate_v1.md)：definition

**不应出现**：当天超过零点就算延迟。

## dev002 · 单文档

一笔订单的商品明细里，第三项的金额是 50 雷亚尔。因为它的订单内序号是 3，就要算成 150 吗？

预期：`knowledge` → `answered`。

**答案要点**

- 不应乘以 3；该订单项商品金额为 50 BRL
- order_item_id 是订单内序号，不是数量；其他订单项金额另行求和

**依据**

- [schema_order_items v1](../../../knowledge/retail_ops/schema/order_items.md)：订单项、商品金额与运费字段

**不应出现**：order_item_id 是购买数量；该项金额为 150 BRL。

## dev003 · 单文档

有一条付款记录，金额 300 雷亚尔，分 3 期。统计付款金额时到底算 300 还是 900？

预期：`knowledge` → `answered`。

**答案要点**

- 计 300 BRL
- 分期期数不参与 payment_value 乘算，支付记录序号也不是分期期数

**依据**

- [schema_order_payments v1](../../../knowledge/retail_ops/schema/order_payments.md)：支付记录、方式与分期字段

**不应出现**：金额为 900 BRL；从此记录推断三笔已到账流水。

## dev004 · 单文档

我想知道有多少不同的人买过东西。同一个人买了好几次只算一个，应该怎么数？不用现在查具体数字。

预期：`knowledge` → `answered`。

**答案要点**

- 同一个人跨订单购买多次只计一个客户，不能用订单数当客户数
- 实现上关联客户表使用 customer_unique_id 去重；不要求用户理解或指定该字段

**依据**

- [schema_dimensions v1](../../../knowledge/retail_ops/schema/dimensions.md)：customers：客户与收货地区

**不应出现**：customer_id 就是跨订单唯一客户标识。

## dev005 · 单文档

假设有 4 笔已经送到的订单，三笔分别给了 5 分、2 分、1 分，还有一笔没评价。平均几分？低分占多少？有多少订单给了评价？

预期：`knowledge` → `answered`。

**答案要点**

- 平均分为 8/3，展示 2.67
- 1、2 分算低分，低评分率 2/3，展示 66.67%
- 覆盖率 3/4，展示 75.00%；无评价不作 0 分

**依据**

- [metric_order_review_score v1](../../../knowledge/retail_ops/metrics/order_review_score_v1.md)：definition
- [metric_order_review_score v1](../../../knowledge/retail_ops/metrics/order_review_score_v1.md)：示例与输出

**不应出现**：低评分率为 50%；平均分为 2.00；将假设例子称为 Olist 实测。

## dev006 · 单文档

1 月 1 日晚上 6 点下单，第二天早上 6 点送到，送货时间应该算一天还是半天？

预期：`knowledge` → `answered`。

**答案要点**

- 0.5 天，即 12 小时
- 用完整时间差总秒数除以 86400，而不是日历日期相减

**依据**

- [metric_delivery_duration v1](../../../knowledge/retail_ops/metrics/delivery_duration_v1.md)：definition
- [metric_delivery_duration v1](../../../knowledge/retail_ops/metrics/delivery_duration_v1.md)：计算与输出

**不应出现**：跨了一个日历日所以计 1 天。

## dev007 · 跨文档

为什么“已经送到的订单里，商品一共多少钱”和“付款记录一共多少钱”对不上？比较前应该先看什么？

预期：`knowledge` → `answered`。

**答案要点**

- 商品金额默认仅 delivered，支付金额默认全部状态（含 canceled）
- 商品金额对订单项 price 求和、不含运费；支付金额对支付记录求和
- 比较前统一下单期间、地区和订单状态范围，并检查缺失记录；不能把差额直接认定为退款

**依据**

- [metric_delivered_item_amount v1](../../../knowledge/retail_ops/metrics/delivered_item_amount_v1.md)：definition
- [metric_payment_record_amount v1](../../../knowledge/retail_ops/metrics/payment_record_amount_v1.md)：definition
- [guide_join_and_metrics v1](../../../knowledge/retail_ops/guides/join_and_metrics_faq.md)：为什么支付金额和商品金额不一样？

**不应出现**：两指标默认状态范围相同；差额必然是退款。

## dev008 · 跨文档

一个订单买了两件东西，又分两次付款。我把商品明细和付款明细按订单号合在一起后，金额翻倍了，这是为什么？怎么避免？

预期：`knowledge` → `answered`。

**答案要点**

- 直接关联两张明细会形成 4 行并重复金额
- 分别按 order_id 汇总订单项和支付，再关联每单一行结果
- 不能用 SUM(DISTINCT 金额) 作为通用修复，不同记录可能同金额

**依据**

- [schema_order_items v1](../../../knowledge/retail_ops/schema/order_items.md)：订单项、商品金额与运费字段
- [schema_order_payments v1](../../../knowledge/retail_ops/schema/order_payments.md)：支付记录、方式与分期字段
- [guide_join_and_metrics v1](../../../knowledge/retail_ops/guides/join_and_metrics_faq.md)：为什么金额 JOIN 后翻倍？

**不应出现**：直接 JOIN 后求和正确；用 SUM(DISTINCT 金额) 总能解决。

## dev009 · 跨文档

有个订单已经正常送到，也知道它什么时候下的单，但没记录预计哪天到。它能算进平均送货时间吗？还能判断它是不是晚到了吗？

预期：`knowledge` → `answered`。

**答案要点**

- 可参与下单至交付平均时长，前提是下单和实际交付时间有效
- 不能参与延迟率，因为缺少有效预计交付日期
- 因此两个指标有效样本数可能不同，缺预计日期不等于准时

**依据**

- [metric_delivery_duration v1](../../../knowledge/retail_ops/metrics/delivery_duration_v1.md)：订单范围与排除
- [metric_delivered_order_late_rate v1](../../../knowledge/retail_ops/metrics/delivered_order_late_rate_v1.md)：definition

**不应出现**：两个指标必须同一分母；预计日期缺失算准时。

## dev010 · 跨文档

同一个订单先给了 1 分，后来又给了 5 分，但后一次没写评论。统计时算几分？完全没评价的订单怎么算？

预期：`knowledge` → `answered`。

**答案要点**

- 在两个提交时间不同且均有效的情况下选最新的 5 分
- 没有标题或正文不影响有效评分
- 完全没评价的目标订单不进入平均分或低评分率分母，但进入评价覆盖率分母，不记为 0 分

**依据**

- [schema_order_reviews v1](../../../knowledge/retail_ops/schema/order_reviews.md)：使用方式
- [metric_order_review_score v1](../../../knowledge/retail_ops/metrics/order_review_score_v1.md)：每单如何选择一条评价
- [metric_order_review_score v1](../../../knowledge/retail_ops/metrics/order_review_score_v1.md)：definition

**不应出现**：将两次评分平均为 3 分；无文字的 5 分无效；无评价订单按 0 分。

## dev011 · 版本与时间

延迟率 v1 在 2026 年启用，能按它分析 2018 年 1 月下单的订单吗？会不会因为订单更早就不能用？

预期：`knowledge` → `answered`。

**答案要点**

- 可以按显式 v1 分析 2018 年订单
- 文档启用时间是项目规则版本时间，不是订单数据适用起点
- 不能声称这是 Olist 在 2018 年采用的官方历史 KPI

**依据**

- [metric_delivered_order_late_rate v1](../../../knowledge/retail_ops/metrics/delivered_order_late_rate_v1.md)：已交付订单延迟率 v1
- [olist_source_and_scope v1](../../../knowledge/retail_ops/overview/source_and_scope.md)：数据来源

**不应出现**：2018 年早于 2026 年所以不能算；项目规则代表 Olist 当时政策。

## dev012 · 版本与时间

请按延迟率 v2 算 2018 年 1 月 SP 州的数据，并告诉我它与 v1 的变化。

预期：`clarify` → `needs_clarification`。

**答案要点**

- 当前发布知识库只有 v1，无法确认 v2 定义或与 v1 的差异
- 说明缺少 v2 契约，询问是否改用 v1 或提供 v2；本轮不输出冒充 v2 的数值

**依据**

- [olist_source_and_scope v1](../../../knowledge/retail_ops/overview/source_and_scope.md)：公共查询约定（项目 v1）

**不应出现**：编造 v2 条款；静默回退 v1 后标为 v2。

## dev013 · 版本与时间

我想还原“截至 2018 年 1 月 31 日当时已经知道的”SP 州订单延迟率，能直接用当前 Olist 快照吗？下载日期能当观察截止时间吗？

预期：`knowledge` → `answered`。

**答案要点**

- 不能直接声称还原当时状态，静态数据缺少完整状态变化历史且真实观察截止时点未知
- 下载日期不能作为业务观察截止时间
- 可另行按固定快照分析 1 月下单订单的最终可见交付结果，但必须标明两种问题不同

**依据**

- [olist_source_and_scope v1](../../../knowledge/retail_ops/overview/source_and_scope.md)：不具备的数据
- [metric_delivered_order_late_rate v1](../../../knowledge/retail_ops/metrics/delivered_order_late_rate_v1.md)：查询参数与时间

**不应出现**：下载日期等于观察截止时点；当前快照能完整还原当时已知状态。

## dev014 · 联合查数

2018 年 1 月下的订单，SP 和 RJ 这两个州的客户，哪里的订单更容易晚到？给我各自晚到的比例和用来计算的订单数。

预期：`hybrid` → `answered`。

**答案要点**

- 按 2018 年 1 月下单时间和客户州筛选，使用当前默认 v1
- 对有效已交付订单比较实际与预计日期；SP 为 3.43%，RJ 为 13.06%，RJ 晚到比例更高
- 展示两州延迟/有效订单数，说明仅统计有效已交付订单；排除数、原因和快照保留在详情中

**依据**

- [metric_delivered_order_late_rate v1](../../../knowledge/retail_ops/metrics/delivered_order_late_rate_v1.md)：definition
- [metric_delivered_order_late_rate v1](../../../knowledge/retail_ops/metrics/delivered_order_late_rate_v1.md)：排除与输出
- [metric_delivered_order_late_rate v1](../../../knowledge/retail_ops/metrics/delivered_order_late_rate_v1.md)：客户州与关联
- [schema_orders v1](../../../knowledge/retail_ops/schema/orders.md)：订单与配送字段

**不应出现**：使用卖家州；按交付月份筛选；将数字称为实时或当时已知结果。

**参考数值**（用于后台核对，主回答无需展示所有实现字段）：

```json
[
  {
    "customer_state": "RJ",
    "cohort_order_count": 893,
    "eligible_order_count": 850,
    "late_order_count": 111,
    "excluded_order_count": 43,
    "not_delivered": 43,
    "invalid_delivery_time": 0,
    "invalid_time_order": 0,
    "late_rate": 0.13058823529411764,
    "late_rate_display": "13.06%"
  },
  {
    "customer_state": "SP",
    "cohort_order_count": 3052,
    "eligible_order_count": 2975,
    "late_order_count": 102,
    "excluded_order_count": 77,
    "not_delivered": 77,
    "invalid_delivery_time": 0,
    "invalid_time_order": 0,
    "late_rate": 0.03428571428571429,
    "late_rate_display": "3.43%"
  }
]
```

## dev015 · 联合查数

2018 年 1 月下的订单里，SP 州客户已经收到货的那些订单，商品一共多少钱？不算运费，用雷亚尔告诉我。

预期：`hybrid` → `answered`。

**答案要点**

- 2018 年 1 月下单、客户州 SP、已交付订单的商品金额为 368611.43 BRL
- 不含运费，不乘明细序号，不扣未知退款；不称为利润
- 计数、缺失/无效情况和快照可放在详情中，不强制主回答逐项列出

**依据**

- [metric_delivered_item_amount v1](../../../knowledge/retail_ops/metrics/delivered_item_amount_v1.md)：definition
- [metric_delivered_item_amount v1](../../../knowledge/retail_ops/metrics/delivered_item_amount_v1.md)：输出与关联
- [schema_order_items v1](../../../knowledge/retail_ops/schema/order_items.md)：订单项、商品金额与运费字段

**不应出现**：把支付金额当商品金额；包含运费；称为利润或扣退款净额。

**参考数值**（用于后台核对，主回答无需展示所有实现字段）：

```json
[
  {
    "cohort_order_count": 3052,
    "delivered_order_count": 2975,
    "valid_item_count": 3379,
    "contributing_order_count": 2975,
    "missing_item_order_count": 0,
    "invalid_item_count": 0,
    "amount_cents": 36861143,
    "amount_brl_display": "368611.43"
  }
]
```

## dev016 · 联合查数

2018 年 1 月一共有多少订单？再看看这些订单用各种付款方式各付了多少钱、各有多少条付款记录、涉及多少订单。不同方式的订单数能直接加起来吗？

预期：`hybrid` → `answered`。

**答案要点**

- 按 2018 年 1 月下单统计，默认全部状态和客户州，共 7269 笔订单，应简短说明包含全部状态
- 按付款方式报告金额、付款记录数和不同订单数，不乘分期数；缺失/无效统计可放在详情中
- 各方式金额可以相加，但不同订单数可能重叠，不能相加作为总订单数

**依据**

- [metric_payment_record_amount v1](../../../knowledge/retail_ops/metrics/payment_record_amount_v1.md)：definition
- [metric_payment_record_amount v1](../../../knowledge/retail_ops/metrics/payment_record_amount_v1.md)：参数与统计范围
- [schema_order_payments v1](../../../knowledge/retail_ops/schema/order_payments.md)：支付记录、方式与分期字段

**不应出现**：默认只取 delivered；把分期数乘到金额上；各方式订单数之和就是总订单数。

**参考数值**（用于后台核对，主回答无需展示所有实现字段）：

```json
[
  {
    "payment_type": "boleto",
    "payment_record_count": 1518,
    "matched_order_count": 1518,
    "invalid_payment_count": 0,
    "amount_cents": 20484466,
    "cohort_order_count": 7269,
    "missing_payment_order_count": 0,
    "amount_brl_display": "204844.66"
  },
  {
    "payment_type": "credit_card",
    "payment_record_count": 5520,
    "matched_order_count": 5511,
    "invalid_payment_count": 0,
    "amount_cents": 86888038,
    "cohort_order_count": 7269,
    "missing_payment_order_count": 0,
    "amount_brl_display": "868880.38"
  },
  {
    "payment_type": "debit_card",
    "payment_record_count": 109,
    "matched_order_count": 109,
    "invalid_payment_count": 0,
    "amount_cents": 1154355,
    "cohort_order_count": 7269,
    "missing_payment_order_count": 0,
    "amount_brl_display": "11543.55"
  },
  {
    "payment_type": "voucher",
    "payment_record_count": 416,
    "matched_order_count": 304,
    "invalid_payment_count": 0,
    "amount_cents": 2973559,
    "cohort_order_count": 7269,
    "missing_payment_order_count": 0,
    "amount_brl_display": "29735.59"
  }
]
```

## dev017 · 联合查数

2018 年 1 月下的订单里，SP 和 RJ 两个州已经收货的客户，评价怎么样？比较一下平均分、低分比例，还有多少订单给了评价。

预期：`hybrid` → `answered`。

**答案要点**

- 范围是 2018 年 1 月下单、客户州 SP/RJ 且已交付的订单，先每单选最新有效评价
- SP 平均 4.19 分、低分 11.91%、覆盖率 99.36%；RJ 平均 3.86 分、低分 21.43%、覆盖率 98.82%
- 解释低分指 1～2 分，没评价不记零；计数与多候选处理可放在详情中，不推断配送造成评分变化

**依据**

- [metric_order_review_score v1](../../../knowledge/retail_ops/metrics/order_review_score_v1.md)：每单如何选择一条评价
- [metric_order_review_score v1](../../../knowledge/retail_ops/metrics/order_review_score_v1.md)：definition
- [metric_order_review_score v1](../../../knowledge/retail_ops/metrics/order_review_score_v1.md)：示例与输出
- [schema_order_reviews v1](../../../knowledge/retail_ops/schema/order_reviews.md)：实际关联情况

**不应出现**：直接平均全部评价记录；未评价记零；按全部目标订单计算低评分率。

**参考数值**（用于后台核对，主回答无需展示所有实现字段）：

```json
[
  {
    "customer_state": "RJ",
    "target_order_count": 850,
    "reviewed_order_count": 840,
    "low_score_order_count": 180,
    "score_sum": 3241,
    "no_review_order_count": 10,
    "only_invalid_review_order_count": 0,
    "multiple_candidate_order_count": 7,
    "mean_score": 3.8583333333333334,
    "mean_score_display": "3.86",
    "low_score_rate": 0.21428571428571427,
    "low_score_rate_display": "21.43%",
    "review_coverage_rate": 0.9882352941176471,
    "review_coverage_rate_display": "98.82%"
  },
  {
    "customer_state": "SP",
    "target_order_count": 2975,
    "reviewed_order_count": 2956,
    "low_score_order_count": 352,
    "score_sum": 12387,
    "no_review_order_count": 19,
    "only_invalid_review_order_count": 0,
    "multiple_candidate_order_count": 13,
    "mean_score": 4.190460081190798,
    "mean_score_display": "4.19",
    "low_score_rate": 0.11907983761840325,
    "low_score_rate_display": "11.91%",
    "review_coverage_rate": 0.9936134453781512,
    "review_coverage_rate_display": "99.36%"
  }
]
```

## dev018 · 边界处理

2018 年 1 月这些订单一共赚了多少利润？

预期：`out_of_scope` → `insufficient_evidence`。

**答案要点**

- 当前数据缺少计算利润需要的成本等信息，无法给出利润金额
- 不能将商品金额、支付金额或两者差额冒充利润；可说明能查询哪些金额，但不擅自替代原请求

**依据**

- [olist_source_and_scope v1](../../../knowledge/retail_ops/overview/source_and_scope.md)：不具备的数据

**不应出现**：将商品金额或支付金额称为利润；假定利润率或编造成本后输出利润。

## dev019 · 边界处理

2018 年 1 月 SP 州卖了多少钱？

预期：`clarify` → `needs_clarification`。

**答案要点**

- 先确认销售额指已交付订单商品金额还是支付记录金额（两者口径不同）
- 保留已给定期间与 SP 范围，不重新询问这些条件
- 确认前不任意返回某一个指标的数值

**依据**

- [guide_join_and_metrics v1](../../../knowledge/retail_ops/guides/join_and_metrics_faq.md)：用户只说“销售额”或“退款率”怎么办？

**不应出现**：任意选择商品金额或支付金额直接作答。

## dev020 · 边界处理

帮我比较一下 SP 和 RJ 的订单，哪个州更容易晚到？

预期：`clarify` → `needs_clarification`。

**答案要点**

- 询问下单统计期间的起止日期或具体月份
- 已有指标版本和地区范围无需重复询问
- 不自行选 2018 年 1 月、全历史或当前月份

**依据**

- [metric_delivered_order_late_rate v1](../../../knowledge/retail_ops/metrics/delivered_order_late_rate_v1.md)：查询参数与时间

**不应出现**：默认沿用其他题的 2018 年 1 月；未澄清就查询任意期间。
