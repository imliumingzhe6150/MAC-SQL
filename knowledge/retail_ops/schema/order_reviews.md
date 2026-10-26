---
doc_id: schema_order_reviews
version: 1
title: 评价字段与订单关联
doc_type: schema
status: published
origin_type: source_and_snapshot
authority: dataset_documentation
published_at: 2026-10-25
effective_from: 2026-10-25
effective_to: null
business_domain: reviews
---

# 评价字段与订单关联

文件：`olist_order_reviews_dataset.csv`，共 99,224 行，每行一条评价记录；来源见[数据范围说明](../overview/source_and_scope.md)。

| 字段 | 类型 | 含义 | 空值数 |
| --- | --- | --- | ---: |
| `review_id` | 文本 | 评价标识；本快照不能作为单列唯一键 | 0 |
| `order_id` | 文本 | 对应订单，关联订单表 | 0 |
| `review_score` | 整数 | 满意度评分，实测为 1～5 | 0 |
| `review_comment_title` | 文本 | 评价标题，可缺失 | 87,656 |
| `review_comment_message` | 文本 | 评价正文，可缺失 | 58,247 |
| `review_creation_date` | 日期时间 | 评价调查创建时间，不是客户提交答案的时间 | 0 |
| `review_answer_timestamp` | 日期时间 | 客户提交评价答案的时间 | 0 |

## 实际关联情况

- 覆盖 98,673 笔订单，订单引用均可在订单表中找到。
- 547 笔订单有多条评价；768 笔订单没有评价记录。
- 行数比不同 `review_id` 的数量多 814；没有整行完全重复记录。不能仅按 `review_id` 去重后直接计算订单评分。
- 评分 1、2、3、4、5 分分别有 11,424、3,151、8,179、19,142、57,328 条记录。这是评价记录分布，不是每单只取一次的评分分布。

## 使用方式

客户有评分但没写文字时，仍可参与评分统计。文字缺失不等于低分，没有评价的订单也不是 0 分。

计算订单平均评分或低评分率时，先根据[评分契约](../metrics/order_review_score_v1.md)在每笔订单内选择一条评价，再汇总；不能直接把全部评价行平均后称为订单平均分。

调查创建、回答、交付是不同时间。数据卡描述的评价收集流程不能被当作每条记录都满足某个时间顺序的保证。本阶段按下单订单群分析快照中的评价，不声称重建当时尚未收到的评价。

评价文本是客户表达，可用于描述问题线索，不是正式指标定义或政策来源。配送与评分的关系只能作为描述性关联。
