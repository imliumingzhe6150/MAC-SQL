
* **先接通 DeepSeek。**
  MAC-SQL 原来的调用方式与你 DIN-SQL 中的 DeepSeek 接口不同。先参考你已经写好的 `din-sql/llm_client.py`，理解它怎样调用 DeepSeek，再看 MAC-SQL 的 `core/llm.py`，找到实际发送请求的 `api_func()`。这一步的目标是让 MAC-SQL 的模型调用走你已经用过的 DeepSeek 接口。
* **准备只含一道题的输入文件。**
  从现有 Spider `dev.json` 中取出上面这道题，保留它的完整数据结构，放进一个只有一个元素的列表。这样批量入口依然能用，但只会处理一题。不要修改原来的 `dev.json`。
* **通过 `run.py` 启动这道题。**
  给它指定 Spider 数据集、单题输入文件、数据库目录、`tables.json`、结果文件和日志文件。不要直接运行当前默认的 `run.sh`，因为它配置的是另一个示例。
* **查看这一次运行的过程。**
  重点确认：Selector 是否调用了模型、Decomposer 生成了什么 SQL、Refiner 执行是否成功、最终 `pred` 是什么。首题跑通后，再考虑 JOIN 和嵌套题。
