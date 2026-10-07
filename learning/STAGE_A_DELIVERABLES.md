# 阶段 A 交付物与过关参考答案

日期：2026-10-05。依据：当前本地 MAC-SQL 的 `run.py`、`core/chat_manager.py` 与 `core/agents.py`。

学习状态：按你的反馈，阶段 A 的源码阅读已完成。本文件是复习与自测参考，不代表已经进行了独立闭卷考核。下面的手工轨迹不是模型运行日志。

## 1. 一页流程图

![MAC-SQL 阶段 A 流程图](</Users/liumingzhe/Desktop/Learning Agent/MAC-SQL/learning/stage_a_flowchart.png>)

这张图画的是官方代码的正常主路径。三个 Agent 共享同一个消息字典，Agent 修改 `send_to`，ChatManager 负责实际调用。解析错误退出和原版异常分支的问题见第 4 节。

## 2. 字段说明：一张消息怎样被逐步补全

| 字段 | 含义 | 主要由谁写入 | 主要由谁读取 |
| --- | --- | --- | --- |
| `idx` | 本次样本编号 | 初始化函数 | 日志、保存与续跑逻辑 |
| `db_id` | 对应哪一个数据库 | 初始化函数 | Selector、Refiner |
| `query` | 自然语言问题；不是原始 Spider 的 `item['query']` | 初始化函数 | 三个 Agent |
| `evidence` | 可选背景知识；Spider 初始化为空字符串 | 初始化函数 | 相关提示词，Spider 分解模板不使用它 |
| `extracted_schema` | 预先提供或模型输出的 Schema 选择决定；初始 `{}` | 初始化函数、Selector | Selector |
| `ground_truth` | 数据集标准 SQL | 初始化函数 | 评测或日志；不应被放入生成提示词 |
| `difficulty` | 根据标准 SQL 结构计算的难度 | 初始化函数 | 日志与统计，不是模型预测的分类 |
| `send_to` | 下一步把消息交给谁 | ChatManager、三个 Agent | ChatManager 与 Agent 的入口判断 |
| `chosen_db_schem_dict` | 按代码保留规则整理后的实际表列 | Selector | 日志、筛选分析 |
| `desc_str` | 给模型看的 Schema 描述文本 | Selector | Decomposer、Refiner |
| `fk_str` | 外键关系文本 | Selector | Decomposer、Refiner |
| `pruned` | 本次是否进入模型筛选分支 | Selector | 日志与分析；不保证实际压缩成功 |
| `qa_pairs` | Decomposer 的完整响应字符串 | Decomposer | 日志、分解过程分析 |
| `final_sql` | Decomposer 提取出的最后一个 SQL 块 | Decomposer | Refiner 首次执行时 |
| `pred` | Refiner 当前保存的 SQL 或错误文本 | Refiner | 后续 Refiner、结果保存、评测 |
| `fixed` | 是否发生过修复；Decomposer 先设为 `False` | Decomposer、Refiner | 日志；`True` 不保证正确 |
| `try_times` | Refiner 在相应处理分支中累加的次数 | Refiner | 日志；不等于修复模型调用次数 |

初始时不存在的键，可以在后续步骤通过 `message['新键'] = value` 创建。字典原地修改，所以 `talk()` 不必返回一个新的消息。

### 每个角色的五项说明

| 角色 | 输入 | 输出 | 工具 | 下一跳与失败处理 |
| --- | --- | --- | --- | --- |
| Selector | 问题、数据库、可选已有选择、evidence | Schema 描述、外键、实际表列、筛选标记 | Schema 文件、SQLite 内容读取；满足条件时调用模型 | 正常交给 Decomposer；模型筛选异常时可回退空选择，再构造 Schema |
| Decomposer | 问题、Schema、外键，BIRD 还用 evidence | 完整响应 `qa_pairs`、提取的 `final_sql`、`fixed=False` | 模型、SQL 文本解析器 | 交给 Refiner；找不到 SQL 可得到错误字符串；不执行子 SQL |
| Refiner | 当前 SQL、问题、Schema、外键、数据库 | `pred`、次数、修复标记、路由 | SQLite；需要修复时调用模型 | 无需修复交给 System；修改后交给 Refiner；原版异常处理有缺陷 |

`error_info`（含执行数据或报错）、`is_need` 和 `is_timeout` 是 Refiner 内部局部变量，并不会由这段原版代码自动完整写入 `message`。阶段 B 要保存执行证据时，需要另外记录。

## 3. 两条手工追踪

以下 SQL 是教学参考写法，未声称是本次模型生成。数据库读取检查是实际执行过的只读检查。

### EASY：样本 0

问题：`How many singers do we have?`（共有多少位歌手？）

数据库：`concert_singer`。所需表是 `singer`，不需要 JOIN。

```sql
SELECT COUNT(*) FROM singer;
```

| 时点 | 主要读取 | 主要写入 / 路由 |
| --- | --- | --- |
| 初始化 | 数据集中的问题、数据库 ID | `idx=0`、`query`、`db_id`、`extracted_schema={}`、`send_to=System` |
| ChatManager 入口 | `send_to` | `System → Selector` |
| Selector | 数据库 Schema、已有选择、问题 | `desc_str`、`fk_str`、实际表列、`pruned=False`；转到 Decomposer |
| Decomposer | 问题、`desc_str`、`fk_str` | 假设生成上面的 SQL：写入 `qa_pairs`、`final_sql`、`fixed=False`；转到 Refiner |
| Refiner | 尚无 `pred`，所以取 `final_sql` | 执行成功后把当前 SQL 写入 `pred`，`try_times=1`，转到 System |
| ChatManager | 轮末 `send_to=System` | 提前退出循环 |

数据库 Schema 有 4 张表、21 个实际列；原代码整数平均列数为 `21 // 4 = 5`。因为平均列数不超过 6、总列数不超过 30，所以无需模型筛选。Selector 仍然运行，只是没有调用筛选模型。

本次手写 SQL 的数据库检查结果为 `[(6,)]`。这是后面核对首题的参考值，不应作为这道题的答案塞给模型。

正常无错误时，该题可以在第一轮依次完成三个角色。题目处理本身只有一次 Decomposer 模型调用；原版 `ChatManager` 初始化的 `ping_network()` 还会额外调用一次模型，不能把它算成某个 Agent 在回答此题。

### JOIN：样本 22

问题：`Show the stadium name and the number of concerts in each stadium.`

按这个数据集参考查询的口径，列出有演唱会记录的体育场名称及演唱会数量；如果另一个业务问题要求包含零场次体育场，需要重新考虑 LEFT JOIN 和计数方式。

涉及两张表：`stadium` 提供名称，`concert` 提供每场演唱会记录。连接关系：

```text
concert.Stadium_ID → stadium.Stadium_ID
```

教学参考 SQL：

```sql
SELECT s.Name, COUNT(*)
FROM concert AS c
JOIN stadium AS s ON c.Stadium_ID = s.Stadium_ID
GROUP BY s.Stadium_ID, s.Name;
```

| 时点 | 主要变化 |
| --- | --- |
| 初始化 / 入口 | 问题换为 JOIN 题，仍是 `System → Selector` |
| Selector | 同一个小数据库，仍跳过模型筛选；保留相关表列与外键上下文 |
| Decomposer | 需要把演唱会与体育场连接，再按体育场分组计数；写入完整响应及最终 SQL |
| Refiner | 先执行 `final_sql`；成功则写 `pred` 并转到 System |

本次手写查询返回 5 行：Stark's Park=1、Somerset Park=2、Recreation Park=1、Balmoor=1、Glebe Park=1。没有排序要求，显示顺序不作为正确性依据。

**它不必进入第二轮。** JOIN 题更复杂，并不意味着自动增加一次调度轮次或必须调用修复模型。

这个问题已经出现在官方 Spider 分解提示词的示例中，所以适合讲解流程，不适合作为独立能力验证。阶段 B 的 JOIN 练习改用样本 33。

### 补充：如果首次 SQL 写错了列名

```text
第一轮：Selector → Decomposer → Refiner
        SQL 报错 → 调用修复模型 → 更新 pred → send_to=Refiner

第二轮：Selector 与 Decomposer 不匹配 send_to，跳过
        Refiner 执行 pred → 成功 → send_to=System → 结束
```

这是条件路径示例，不是本次真实模型修复记录。

## 4. 阶段 A 过关标准：参考答案

### 问题 1：send_to 怎样变化？

初始化时是 `System`。`ChatManager.start()` 把它改成 `Selector`。Selector 完成数据库上下文准备后改为 `Decomposer`；Decomposer 保存生成 SQL 后改为 `Refiner`。Refiner 若无需修复，则改成 `System`；如果产生修复 SQL，则保持为 `Refiner`，等待下一轮验证。

角色负责写入路由状态，调度器按角色列表顺序检查并调用。`System` 是标记，不是列表中的第四个 Agent。

### 问题 2：为什么 Refiner 会再次收到消息？

因为上一轮修复后，Refiner 把 `send_to` 设为自己的名称。外层 `ChatManager.start()` 还没有达到轮数上限，也没有收到 `System` 结束信号，就会继续下一轮。

下一轮遍历时，只有 Refiner 与 `send_to` 匹配。它优先取 `pred`，所以执行的是上一轮修改后的 SQL，而不是重新执行最初的 `final_sql`。Refiner 本身没有递归调用自己。

### 问题 3：什么情况下停止？

正常控制逻辑有两个主要出口：

1. 某轮结束时 `send_to=System`，`ChatManager` 执行 `break`。
2. 达到 `MAX_ROUND`，即使还没发出 System 信号，循环也会自然结束。当前常量是 3，表示调度轮数，不是固定三次模型调用。

Refiner 中，无需修复会发出 System 信号；检查到 SQL 文本包含小写 `error` 也会提前发出该信号。未被处理的异常可能直接打断流程，但这不是成功结束。

原作者还试图在执行超时时停止。不过当前代码在异常后可能使用未赋值的 `error_info`，所以应当指出这是缺陷，不能回答“超时已被可靠处理”。

达到轮数上限时，最后一次修复生成的 SQL 可能尚未执行；因此程序停止不代表预测正确，甚至不代表最后版本已经执行。

### 可直接口述的完整答案

> 一道题通过同一个消息字典在三个角色之间传递。send_to 初始是 System，调度器先改成 Selector。Selector 准备 Schema 后交给 Decomposer，Decomposer 生成 SQL 后交给 Refiner。Refiner 执行成功且按当前规则无需修复时交回 System；需要修复时把新 SQL 存入 pred，并把下一跳设为 Refiner。外层调度器在下一轮再次调用它，执行这个新 SQL。收到 System 信号或者达到 MAX_ROUND 都会结束，但结束不等于答案正确，原版最后一次修改还可能没有被验证。

## 5. 指南中另外四道自测题的答案

| 自测题 | 参考答案 |
| --- | --- |
| Selector 没调用模型时，Schema 从哪里来？ | `_get_db_desc_str()` 根据 Schema 文件、数据库信息及可选已有选择构造。跳过筛选不等于没有 Schema，也不等于没有运行 Selector。 |
| Decomposer 一次回复有多个 SQL，用哪一个？ | 当前解析器提取最后一个 `sql` 代码块，放入 `final_sql`。前面的子 SQL 不会自动逐个执行。 |
| Refiner 修改 SQL 后，谁安排下一次执行？ | Refiner 写 `send_to=Refiner`，由 ChatManager 的下一轮遍历安排。 |
| SQL 能执行却答错，会不会发现？ | Spider 分支通常不会仅靠这一检查发现。它检查执行是否返回 `data`，不拿 Gold 判断语义。需要独立评测。 |

## 6. DIN-SQL 与 MAC-SQL 的纠错区别

| 对比维度 | DIN-SQL 文本式 self-correction | MAC-SQL Refiner |
| --- | --- | --- |
| 反馈来源 | 模型阅读问题、Schema 和 SQL 后再检查 | SQLite 的执行结果或错误，再按规则决定是否调用模型 |
| 模型是否一定参与本次检查 | 文本纠错步骤通常会再次调用模型 | SQL 无需修复时可以不调用修复模型 |
| 能直接发现的错误 | 依赖模型识别可疑写法与逻辑 | 数据库可以直接报告语法错误、缺少表列等问题 |
| 共同限制 | 模型检查不保证语义正确 | 执行成功也不保证语义正确 |

这里比较的是纠错阶段自身。DIN-SQL 实验另有离线执行评测，不应把评测器与生成过程中的 self-correction 混为一谈。

下一步：[阶段 B 首题实践](</Users/liumingzhe/Desktop/Learning Agent/MAC-SQL/learning/STAGE_B_FIRST_LESSON.md>)。
