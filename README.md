## 📖Introduction

This is the official repository for the paper [&#34;MAC-SQL: A Multi-Agent Collaborative Framework for Text-to-SQL&#34;](https://arxiv.org/abs/2312.11242).

In this paper, we propose a multi-agent collaborative Text-to-SQL framework MAC-SQL, which comprises three agents: the **Selector**, the **Decomposer**, and the **Refiner**.

<img src="./assets/framework.jpg" align="middle" width="95%">

## 🧪 本地学习复现：DeepSeek + Spider

> 本节记录个人学习环境中的小样本复现，不是 MAC-SQL 论文的官方实验结果。

本实验使用同一 DeepSeek 模型，对比直接生成 SQL 的 baseline、基于 DIN-SQL 四阶段思路的简化实现，以及当前 MAC-SQL 完整流程。

### 实验设置

- 数据集：Spider dev 中固定的 30 道题，输入见 `data/spider/macsql_30.json`。
- 题型分组：EASY、NON-NESTED、NESTED 各 10 道。这是按 Gold SQL 结构预先划分的学习分组，不是 Spider 官方难度标签。
- 公平性：三种方法使用同一批题、同一数据库和同一模型。
- 评测：在本地 SQLite 中分别执行预测 SQL 和 Gold SQL。有 `ORDER BY` 时比较行顺序；无排序要求时忽略行顺序，但保留重复行的计数。
- 当前 MAC-SQL 的 Spider `Decomposer` 提示词直接生成最终 SQL，不要求显式输出多个子问题。

### 实验结果

| 方法                       |    执行成功率 | EASY 结果匹配 | NON-NESTED 结果匹配 | NESTED 结果匹配 |   总结果匹配率 | 模型调用次数 |
| -------------------------- | ------------: | ------------: | ------------------: | --------------: | -------------: | -----------: |
| Baseline                   | 30/30（100%） |         10/10 |                6/10 |            9/10 | 25/30（83.3%） |        约 30 |
| DIN-SQL 简化实现（修正后） | 30/30（100%） |         10/10 |                8/10 |            9/10 | 27/30（90.0%） |       约 120 |
| MAC-SQL（当前完整流程）    | 30/30（100%） |         10/10 |                9/10 |            9/10 | 28/30（93.3%） |           30 |

DIN-SQL 的调用次数按 Schema Linking、Classification / Decomposition、SQL Generation 和 Self-Correction 四个固定阶段推算。MAC-SQL 的 30 次调用来自 `api_trace.json` 的实际记录；共使用 45,901 个 prompt tokens 和 12,532 个 response tokens，合计 58,433 tokens。
