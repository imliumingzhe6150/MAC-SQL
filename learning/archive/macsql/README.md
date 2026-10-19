# 原 MAC-SQL 学习记录（归档）

归档日期：2026-10-19。这里保留旧阶段的实验说明和学习笔记；当前运行入口见 [LangGraph 使用说明](../../../MAC_with_LangGraph/README.md)。

原 MAC-SQL 源码、评测器、演示与训练脚本已从当前工作目录移除，可在[清理前提交](https://github.com/imliumingzhe6150/MAC-SQL/tree/1ad71be68fbf8a9545a2fedf1fef4c18bea002e2)中查看。

- [源码学习笔记](STAGE_A_DELIVERABLES.md)
- [首题实践笔记](codex.md)
- [原流程图](stage_a_flowchart.png)

`LEARNING_GUIDE.md` 保留为本地学习资料，继续不纳入 Git。归档笔记中的旧路径用于对应历史代码。

以下是清理前根 README 的历史内容，其中的“官方仓库”表述来自原项目介绍。

---

## 📖Introduction

This is the official repository for the paper [&#34;MAC-SQL: A Multi-Agent Collaborative Framework for Text-to-SQL&#34;](https://arxiv.org/abs/2312.11242).

In this paper, we propose a multi-agent collaborative Text-to-SQL framework MAC-SQL, which comprises three agents: the **Selector**, the **Decomposer**, and the **Refiner**.

[原 MAC-SQL 框架图](https://github.com/imliumingzhe6150/MAC-SQL/blob/1ad71be68fbf8a9545a2fedf1fef4c18bea002e2/assets/framework.jpg)

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
