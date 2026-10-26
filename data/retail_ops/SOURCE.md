# Olist 数据来源与下载记录

- 数据集：Brazilian E-Commerce Public Dataset by Olist
- 发布者：Olist
- 官方来源：[Kaggle 数据集](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- 下载接口：`https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce`
- 下载完成后的记录时间（Asia/Shanghai）：2026-10-25T22:24:29.311685+08:00
- 下载时官方 API 显示的版本：2
- 官方元数据最后更新时间：2021-10-01T19:08:27.97Z
- 官方标注许可：CC BY-NC-SA 4.0
- 元数据接口：`https://www.kaggle.com/api/v1/datasets/list?search=olist`
- 原始压缩包：`raw/olist/brazilian-ecommerce.zip`
- 压缩包大小：44,717,580 字节（与官方元数据一致）
- 压缩包 SHA-256：`967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784`

## 校验与处理

已通过 ZIP CRC 完整性校验，解压得到 9 个原始 CSV；未清洗、改写或筛除记录。压缩包与 CSV 保留在 `raw/olist/`，该原始数据目录已加入 Git 忽略规则。

[download_manifest.json](download_manifest.json) 记录压缩包及各 CSV 的字节数、SHA-256、CSV 解析后的数据行数（不含表头）与字段列表。行数按 CSV 记录统计，避免评价文本内换行造成误计。以下清单仅为下载核验，不代表已完成数据质量剖析。

| 文件 | 数据行数 | 字段数 |
| --- | ---: | ---: |
| `olist_customers_dataset.csv` | 99,441 | 5 |
| `olist_geolocation_dataset.csv` | 1,000,163 | 5 |
| `olist_order_items_dataset.csv` | 112,650 | 7 |
| `olist_order_payments_dataset.csv` | 103,886 | 5 |
| `olist_order_reviews_dataset.csv` | 99,224 | 7 |
| `olist_orders_dataset.csv` | 99,441 | 8 |
| `olist_products_dataset.csv` | 32,951 | 9 |
| `olist_sellers_dataset.csv` | 3,095 | 4 |
| `product_category_name_translation.csv` | 71 | 2 |

## 当前边界与下一步

尚未导入 SQLite、清洗、抽样或生成开发题。下一步检查订单、订单项、支付表的键、关联基数、缺失值及日期覆盖，再完成数据字典与指标契约。

下载时间不代表业务数据观察截止时间；本数据为历史静态快照。项目自建分析口径不属于 Olist 官方制度。
