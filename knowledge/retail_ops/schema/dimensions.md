---
doc_id: schema_dimensions
version: 1
title: 客户、商品、卖家与类别翻译字段
doc_type: schema
status: published
origin_type: source_and_snapshot
authority: dataset_documentation
published_at: 2026-10-25
effective_from: 2026-10-25
effective_to: null
business_domain: dimensions
---

# 客户、商品、卖家与类别翻译字段

字段含义与本次快照检查结果；来源见[数据范围说明](../overview/source_and_scope.md)。以下表名是 SQL 导入时的建议简称。

## customers：客户与收货地区

`olist_customers_dataset.csv` 共 99,441 行，`customer_id` 唯一，所有字段无空值。`customer_unique_id` 有 96,096 个不同值。

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `customer_id` | 文本 | 本次订单使用的客户标识，与订单表关联 |
| `customer_unique_id` | 文本 | 跨订单识别同一客户，用于客户数或复购分析 |
| `customer_zip_code_prefix` | 文本 | 邮编前缀；保留前导零 |
| `customer_city` | 文本 | 客户城市 |
| `customer_state` | 文本 | 客户州缩写，例如 SP、RJ |

统计订单量按 `order_id`，统计独立客户按 `customer_unique_id`，不能用 `customer_id` 替代独立客户数。按客户州统计配送时，不使用卖家州。

## products：商品属性

`olist_products_dataset.csv` 共 32,951 行，`product_id` 唯一。字段名保持原始拼写，两个 `lenght` 不能擅自写成 `length` 来查询原表。

| 字段 | 类型／单位 | 含义 | 空值数 |
| --- | --- | --- | ---: |
| `product_id` | 文本 | 商品标识 | 0 |
| `product_category_name` | 文本 | 葡萄牙语类别名 | 610 |
| `product_name_lenght` | 整数 | 商品名称长度，不是商品名称正文 | 610 |
| `product_description_lenght` | 整数 | 描述长度，不是描述正文 | 610 |
| `product_photos_qty` | 整数 | 商品照片数量 | 610 |
| `product_weight_g` | 数值／克 | 商品重量 | 2 |
| `product_length_cm` | 数值／厘米 | 长度 | 2 |
| `product_height_cm` | 数值／厘米 | 高度 | 2 |
| `product_width_cm` | 数值／厘米 | 宽度 | 2 |

通过订单项的 `product_id` 关联。原表没有名称正文，不能从名称长度生成真实商品名。类别缺失时项目统一显示 `UNKNOWN`，金额统计保留该组。

## sellers：卖家

`olist_sellers_dataset.csv` 共 3,095 行，`seller_id` 唯一，所有字段无空值。

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `seller_id` | 文本 | 卖家标识，与订单项关联 |
| `seller_zip_code_prefix` | 文本 | 卖家邮编前缀 |
| `seller_city` | 文本 | 卖家城市 |
| `seller_state` | 文本 | 卖家州 |

一笔订单可以有不同卖家的订单项。订单整体延迟或整体评分不能直接归责于某一卖家。首版可以按卖家统计其订单项金额，不默认按卖家分摊整笔订单支付金额。

## product_category_name_translation：类别翻译

`product_category_name_translation.csv` 共 71 行，`product_category_name` 唯一。两列分别为葡萄牙语原类别 `product_category_name` 与英文译名 `product_category_name_english`。

用原类别 LEFT JOIN 翻译表。实测 `pc_gamer` 和 `portateis_cozinha_e_preparadores_de_alimentos` 没有翻译行；项目保留原类别作为显示名称，不删除这些商品。源文件带 UTF-8 BOM，读取时使用 `utf-8-sig`，避免第一列名多出不可见字符。

## 地理扩展

`olist_geolocation_dataset.csv` 暂不参与首版指标。客户/卖家表已有州和城市，按州分组无需引入经纬度表。
