"""Read-only project evaluation helper. Writes only a new results directory."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime
from getpass import getpass
import importlib.metadata
import json
import os
from pathlib import Path
import sqlite3
import sys
import time


DEFAULT_PROJECT = Path(__file__).resolve().parents[1]
METHOD_NAMES = {
    "baseline": "旧 Baseline",
    "din_sql": "旧 DIN-SQL",
    "mac_sql": "旧 MAC-SQL",
    "langgraph": "当前 LangGraph",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def redact(value):
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]") if key else value
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


def json_text(value, *, indent=None):
    return json.dumps(redact(value), ensure_ascii=False, indent=indent)


def execute_readonly(path, sql, timeout=10.0):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    deadline = time.monotonic() + timeout
    connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
    try:
        connection.execute("PRAGMA query_only = ON")
        cursor = connection.execute(sql)
        if cursor.description is None:
            raise ValueError("查询未返回结果表")
        return {
            "success": True,
            "columns": [column[0] for column in cursor.description],
            "rows": cursor.fetchall(),
            "error": None,
        }
    finally:
        connection.close()


def compare_rows(predicted_rows, gold_rows, ordered):
    predicted = [tuple(row) for row in predicted_rows]
    gold = [tuple(row) for row in gold_rows]
    return predicted == gold if ordered else Counter(predicted) == Counter(gold)


def load_inputs(project):
    samples = read_json(project / "data/spider/macsql_30.json")
    if len(samples) != 30:
        raise ValueError(f"预期固定 30 题，实际为 {len(samples)} 题")
    keys = [(sample["db_id"], sample["question"]) for sample in samples]
    if len(set(keys)) != len(keys):
        raise ValueError("题集中存在重复 (db_id, question)，无法唯一对齐")

    din_results = project.parent / "din-sql/results"
    paths = {
        "baseline": sorted((din_results / "baseline").glob("sample_*.json")),
        "din_sql": sorted(din_results.glob("sample_*.json")),
    }
    indices = {}
    for method, files in paths.items():
        index = {}
        for path in files:
            result = read_json(path)
            key = (result["database"], result["question"])
            if key in index:
                raise ValueError(f"{method} 存在重复题目：{key}")
            index[key] = result
        indices[method] = index

    old_mac_path = project / "outputs/macsql_30/results.jsonl"
    mac_index = {}
    for line in old_mac_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        result = json.loads(line)
        key = (result["db_id"], result["query"])
        if key in mac_index:
            raise ValueError(f"mac_sql 存在重复题目：{key}")
        mac_index[key] = result
    indices["mac_sql"] = mac_index

    aligned = []
    for sample in samples:
        key = (sample["db_id"], sample["question"])
        predictions = {}
        for method, index in indices.items():
            if key not in index:
                raise ValueError(f"{method} 缺少题目：{key}")
            result = index[key]
            gold_field = "ground_truth" if method == "mac_sql" else "gold_sql"
            if result[gold_field].strip() != sample["query"].strip():
                raise ValueError(f"{method} 的 Gold SQL 与固定题集不同：{key}")
            sql_field = {"baseline": "generated_sql", "din_sql": "corrected_sql", "mac_sql": "pred"}[method]
            predictions[method] = result.get(sql_field)
        aligned.append(predictions)
    return samples, aligned


def evaluate_historical(project, samples, aligned):
    records = []
    for idx, (sample, predictions) in enumerate(zip(samples, aligned)):
        database = project / "data/spider/database" / sample["db_id"] / f"{sample['db_id']}.sqlite"
        gold = execute_readonly(database, sample["query"])
        ordered = bool(sample["sql"]["orderBy"])
        record = {
            "id": idx + 1,
            "idx": idx,
            "db_id": sample["db_id"],
            "question": sample["question"],
            "gold_sql": sample["query"],
            "gold_rows": gold["rows"],
            "ordered": ordered,
            "methods": {},
        }
        for method, sql in predictions.items():
            start = time.perf_counter()
            try:
                if not isinstance(sql, str) or not sql.strip():
                    raise ValueError("历史记录缺少非空 SQL")
                execution = execute_readonly(database, sql)
                matched = compare_rows(execution["rows"], gold["rows"], ordered)
                error = None
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                execution = {"success": False, "columns": [], "rows": [], "error": error}
                matched = False
            record["methods"][method] = {
                "sql": sql,
                "execution": execution,
                "execution_success": execution["success"],
                "result_match": matched,
                "status": "succeeded" if execution["success"] else "failed",
                "elapsed_seconds": round(time.perf_counter() - start, 6),
                "error": error,
            }
        records.append(record)
    return records


def source_model_metadata(project):
    """Read only explicitly non-secret constructor fields; never evaluate source."""
    path = project / "MAC_with_LangGraph/llm.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = {"configuration_source": str(path)}
    allowed = {"temperature", "max_tokens", "timeout", "max_retries", "extra_body", "base_url"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "ChatDeepSeek":
            continue
        for keyword in node.keywords:
            if keyword.arg in allowed:
                try:
                    result[keyword.arg] = ast.literal_eval(keyword.value)
                except (ValueError, TypeError):
                    pass
            elif keyword.arg == "model":
                value = keyword.value
                if isinstance(value, ast.Constant):
                    result["model"] = value.value
                elif isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and value.func.attr == "get":
                    args = value.args
                    if len(args) >= 2 and all(isinstance(arg, ast.Constant) for arg in args[:2]) and args[0].value == "DEEPSEEK_MODEL":
                        result["model"] = os.environ.get("DEEPSEEK_MODEL", args[1].value)
    return result


def summarize(records, *, offline_only, metadata, interrupted=False):
    methods = ["baseline", "din_sql", "mac_sql"] + ([] if offline_only else ["langgraph"])
    summary = {
        "planned_questions": 30,
        "offline_only": offline_only,
        "interrupted": interrupted,
        "comparison": "Gold 顶层有 orderBy 时逐行比较，否则 Counter 多重集比较；固定列顺序。",
        "metadata": metadata,
        "methods": {},
    }
    for method in methods:
        outcomes = [r["methods"][method] for r in records if method in r["methods"]]
        executed = sum(r["execution_success"] for r in outcomes)
        matches = sum(r["result_match"] for r in outcomes)
        summary["methods"][method] = {
            "completed": len(outcomes),
            "execution_successes": executed,
            "result_matches": matches,
            "execution_rate_of_30": executed / 30,
            "match_rate_of_30": matches / 30,
        }
        if method == "langgraph":
            summary["methods"][method]["model_call_attempts"] = sum(r["model_call_attempts"] for r in outcomes)
            summary["methods"][method]["elapsed_seconds"] = round(sum(r["elapsed_seconds"] for r in outcomes), 3)
    if not offline_only:
        summary["mac_to_langgraph"] = {
            "improved_ids": [r["id"] for r in records if "langgraph" in r["methods"] and not r["methods"]["mac_sql"]["result_match"] and r["methods"]["langgraph"]["result_match"]],
            "regressed_ids": [r["id"] for r in records if "langgraph" in r["methods"] and r["methods"]["mac_sql"]["result_match"] and not r["methods"]["langgraph"]["result_match"]],
        }
    return summary


def make_report(summary):
    lines = ["# 固定 30 题对比结果", ""]
    lines.append("本次仅离线重算历史预测，未调用模型。" if summary["offline_only"] else "历史预测重新执行；当前 LangGraph 对同一批 30 题调用模型。")
    if summary["interrupted"]:
        lines.extend(["", "运行被中断，当前 LangGraph 结果未完整；分母仍为计划的 30 题。"])
    lines.extend(["", "| 方法 | 已完成 | 执行成功 | 结果匹配 | 匹配率 |", "|---|---:|---:|---:|---:|"])
    for method, counts in summary["methods"].items():
        lines.append(f"| {METHOD_NAMES[method]} | {counts['completed']}/30 | {counts['execution_successes']}/30 | {counts['result_matches']}/30 | {counts['match_rate_of_30']:.1%} |")
    if "mac_to_langgraph" in summary:
        changes = summary["mac_to_langgraph"]
        lines.extend(["", f"相对旧 MAC-SQL，变对题号（从 1 开始）：{changes['improved_ids']}。", f"变错题号：{changes['regressed_ids']}。"])
        current = summary["methods"]["langgraph"]
        lines.extend([f"模型调用尝试次数：{current['model_call_attempts']}；总运行时间：{current['elapsed_seconds']:.1f} 秒。"])
    lines.extend(["", summary["comparison"], "", "这是本地固定 30 题的结果匹配率，不是 Spider 官方总体成绩。历史模型版本和提示词可能不同；变化不能单独归因于 LangGraph。历史耗时仅为本次 SQL 重执行耗时，不可与当前模型推理耗时比较。", ""])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="完整跑固定 30 题，对比历史 Baseline / DIN / MAC-SQL")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--offline-only", action="store_true", help="只重算已有预测，不导入 LangGraph 或调用模型")
    args = parser.parse_args(argv)
    project = args.project.expanduser().resolve()
    samples, aligned = load_inputs(project)
    records = evaluate_historical(project, samples, aligned)
    metadata = {"project": str(project), "timestamp": datetime.now().astimezone().isoformat(), "python": sys.version.split()[0]}
    metadata["current_model_configuration"] = source_model_metadata(project)
    output = args.output_dir.expanduser().resolve() if args.output_dir else project / "outputs" / ("langgraph_30_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    if output.exists():
        raise FileExistsError(f"输出目录已存在，为避免覆盖请换一个新目录：{output}")

    graph = None
    nodes = None
    original_call = None
    call_count = 0
    if not args.offline_only:
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        sys.path.insert(0, str(project))
        from MAC_with_LangGraph.graph import graph
        from MAC_with_LangGraph import nodes
        for package in ("langgraph", "langchain-deepseek"):
            metadata[package] = importlib.metadata.version(package)
        if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
            os.environ["DEEPSEEK_API_KEY"] = getpass("请输入 DeepSeek API Key（隐藏输入，仅本次进程使用）：").strip()
        if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
            raise ValueError("未输入 DeepSeek API Key，尚未调用模型")
        original_call = nodes.call_llm

        def counted_call(prompt):
            nonlocal call_count
            call_count += 1
            return original_call(prompt)

        nodes.call_llm = counted_call

    output.mkdir(parents=True, exist_ok=False)
    print(f"输出目录：{output}", flush=True)
    interrupted = False
    try:
        with (output / "results.jsonl").open("x", encoding="utf-8") as handle:
            for record in records:
                if not args.offline_only:
                    start = time.perf_counter()
                    calls_before = call_count
                    try:
                        # Gold SQL, rows, and old predictions never enter the graph.
                        result = graph.invoke({"question": record["question"], "db_id": record["db_id"], "retry_count": 0, "max_retries": 3})
                        execution = result.get("execution", {})
                        success = bool(execution.get("success"))
                        matched = success and compare_rows(execution.get("rows", []), record["gold_rows"], record["ordered"])
                        outcome = {"sql": result.get("sql"), "execution": execution, "status": result.get("status"), "retry_count": result.get("retry_count"), "execution_success": success, "result_match": matched, "error": execution.get("error")}
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                        outcome = {"sql": None, "execution": {"success": False, "columns": [], "rows": [], "error": error}, "status": "exception", "retry_count": None, "execution_success": False, "result_match": False, "error": error}
                    outcome["elapsed_seconds"] = round(time.perf_counter() - start, 3)
                    outcome["model_call_attempts"] = call_count - calls_before
                    record["methods"]["langgraph"] = outcome
                    old_match = record["methods"]["mac_sql"]["result_match"]
                    record["mac_to_langgraph"] = {"old_match": old_match, "new_match": outcome["result_match"]}
                    label = "匹配" if outcome["result_match"] else ("不匹配" if outcome["execution_success"] else "运行失败")
                    print(f"[{record['id']:02d}/30] {label} | {outcome['elapsed_seconds']:.1f}s | 模型调用 {outcome['model_call_attempts']} 次", flush=True)
                handle.write(json_text(record) + "\n")
                handle.flush()
    except KeyboardInterrupt:
        interrupted = True
        print("已中断，保留完成的记录并生成汇总。", flush=True)
    finally:
        if nodes is not None and original_call is not None:
            nodes.call_llm = original_call
        summary = summarize(records, offline_only=args.offline_only, metadata=metadata, interrupted=interrupted)
        (output / "summary.json").write_text(json_text(summary, indent=2) + "\n", encoding="utf-8")
        report = make_report(summary)
        (output / "report.md").write_text(redact(report), encoding="utf-8")
    print(redact(report), flush=True)
    return 130 if interrupted else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(redact(f"评测未完成：{type(exc).__name__}: {exc}"), file=sys.stderr)
        raise SystemExit(1)
