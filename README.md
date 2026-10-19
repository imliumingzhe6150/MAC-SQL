# LangGraph SQL 查询工作流

个人学习项目：参考 MAC-SQL 的角色职责，用 LangGraph 实现“自然语言问题 → SQL → SQLite 查询结果”，后续扩展业务口径检索和工具调用。

## 当前能力

- 读取数据库表结构与外键，调用 DeepSeek 生成 SQL。
- 使用 SQLite 只读连接执行查询，每次查询设置约 5 秒的执行时限。
- 执行报错后修正 SQL，最多修正 3 次；每版修正 SQL 都重新执行。
- 提供单题命令行入口与固定 30 题回归入口。

2026-10-18 的固定开发／回归集结果：**执行成功 30/30，结果匹配 29/30（96.7%）**。该轮未触发修正；提示词和模型条件未完全控制，结果变化不能单独归因于 LangGraph。SQL 执行成功也不代表语义正确。

## 快速开始

在项目根目录使用 Python 3.12 环境：

```bash
python3.12 -m venv .venv-langgraph
source .venv-langgraph/bin/activate
python -m pip install -r requirements.txt
```

已有可用的独立环境时，可直接使用该环境，不必重新创建。API Key 从 `DEEPSEEK_API_KEY` 读取，未设置时由运行入口提示隐藏输入。

准备本地 Spider 数据后运行：

```bash
# 单题示例：修改 graph.py 中 initial_state 的 question 和 db_id
python -m MAC_with_LangGraph.graph

# 查看回归参数，不调用模型
python -m MAC_with_LangGraph.regression --help

# 完整 30 题：调用模型，并比较历史预测
python -m MAC_with_LangGraph.regression
```

单题需要 `data/spider/database/<db_id>/<db_id>.sqlite`。完整回归还需要 `data/spider/macsql_30.json`、`outputs/macsql_30/results.jsonl`，以及本项目同级 `din-sql/results/` 中的历史预测。数据、运行输出和虚拟环境不纳入 Git，克隆仓库后需要单独准备。

## 项目结构

```text
MAC_with_LangGraph/               当前实现、回归脚本与详细使用说明
data/                            本地数据
outputs/                         本地实验记录
learning/LANGGRAPH_DEMO.txt       单题演示输出
learning/archive/macsql/          原 MAC-SQL 阶段学习笔记与历史实验说明
NEXT_STEP_LANGGRAPH_PROJECT.md    原项目路线及当前范围说明
requirements.txt                 当前 LangGraph 依赖
```

- [详细运行说明与结果分析](MAC_with_LangGraph/README.md)
- [单题演示输出](learning/LANGGRAPH_DEMO.txt)
- [项目路线](NEXT_STEP_LANGGRAPH_PROJECT.md)
- [旧阶段学习记录](learning/archive/macsql/README.md)

## 第一阶段范围

当前实现保留全部小型 Schema，直接生成最终 SQL。单题模型调用异常直接抛出，由运行者处理；批量回归将单题异常记录为失败后继续。暂不增加 token 统计或完整节点日志。

下一阶段再增加业务口径 RAG、模型自主选择工具等能力。2026-10-18 的原始结果保留在本地 `outputs/langgraph_30_20261018_175344_798075/`。

## 旧代码与来源

2026-10-19 已清理当前实现不再依赖的旧 `core/`、评测器、训练脚本、Web 演示及旧启动入口。[清理前提交](https://github.com/imliumingzhe6150/MAC-SQL/tree/1ad71be68fbf8a9545a2fedf1fef4c18bea002e2)仍保留原代码，可用于查阅或恢复；旧学习记录已归档，数据与历史结果保留在本地。

参考论文：[MAC-SQL: A Multi-Agent Collaborative Framework for Text-to-SQL](https://arxiv.org/abs/2312.11242)。
