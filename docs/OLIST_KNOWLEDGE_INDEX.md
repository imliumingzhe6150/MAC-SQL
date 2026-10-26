# Olist 第一批知识文档

2026-10-25：已整理 12 份正文，统一位于 `knowledge/retail_ops/`。本清单在知识目录之外，用于阅读导航，不作为检索正文。字段字典统一维护在知识目录，`data/retail_ops/DATA_DICTIONARY.md` 保留导航入口。

| 序号 | 文档 | 用途 |
| --- | --- | --- |
| 1 | [数据来源与分析范围](../knowledge/retail_ops/overview/source_and_scope.md) | 历史快照、支持范围、公共时间和单位约定 |
| 2 | [订单与配送字段](../knowledge/retail_ops/schema/orders.md) | 状态、下单、支付批准、交运、交付日期 |
| 3 | [订单项与金额字段](../knowledge/retail_ops/schema/order_items.md) | 商品、卖家、价格、运费和订单项粒度 |
| 4 | [支付字段](../knowledge/retail_ops/schema/order_payments.md) | 支付方式、分期、支付记录粒度 |
| 5 | [客户、商品、卖家与类别翻译](../knowledge/retail_ops/schema/dimensions.md) | 客户身份、地区、商品属性、类别缺失与翻译 |
| 6 | [评价字段](../knowledge/retail_ops/schema/order_reviews.md) | 评分、文本、时间与一单多评价 |
| 7 | [已交付订单延迟率 v1](../knowledge/retail_ops/metrics/delivered_order_late_rate_v1.md) | 有效订单分母、日期比较、排除规则 |
| 8 | [下单至交付平均时长 v1](../knowledge/retail_ops/metrics/delivery_duration_v1.md) | 完整时间差、平均时长及样本范围 |
| 9 | [已交付订单商品金额 v1](../knowledge/retail_ops/metrics/delivered_item_amount_v1.md) | 商品金额、不含运费、按类别和卖家归属 |
| 10 | [支付记录金额 v1](../knowledge/retail_ops/metrics/payment_record_amount_v1.md) | 默认全状态、支付方式分组与缺失记录 |
| 11 | [订单评分、低评分率与覆盖率 v1](../knowledge/retail_ops/metrics/order_review_score_v1.md) | 每单选择最新有效评价、低分阈值与不同分母 |
| 12 | [多表关联与常见误算 FAQ](../knowledge/retail_ops/guides/join_and_metrics_faq.md) | 真实重复关联例子、金额差异与口径澄清 |

## 本批定义的选择

- 商品金额默认已交付订单；支付记录金额默认全部状态。需要对比时显式统一状态范围。
- 配送时长使用下单到交付的完整时间差；延迟率按实际和预计交付的日历日期比较。
- 评分默认已交付订单，每单选择最新提交的有效评价；1～2 分为低分，缺失评价不作 0 分。

这些是项目自建口径，数据集事实和本地实测数量在字段说明中另行陈述。当前只有 v1，没有伪造历史企业规则。

## 当前完成程度

延迟率已经通过参考 SQL 与独立 Python 计算核对。2026-10-26 已编写 [20 道开发题](../evals/retail_ops/dev/DEV_QUESTIONS.md)，其中延迟率、商品金额、支付金额和评分四道联合题的参考结果均经过 SQL 与独立 Python 交叉核对。配送时长目前仍为文档定义。参考计算器不等于已实现业务助手；开发题答案与结果保留在 `evals/retail_ops/`，不进入这批语料。

本批开发题使用完整 Olist v2 固定快照，尚未抽取 30～50 笔订单小样本。后续小样本需另存参考结果；版本比较和冲突测试材料在相应评测准备时单独补充。当前尚未运行 RAG 模型评测，也未完成整个 B0。
