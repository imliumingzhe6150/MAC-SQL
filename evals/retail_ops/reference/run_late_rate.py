"""Run the v1 reference SQL and cross-check it with a separate Python count.

Usage: python3 evals/retail_ops/reference/run_late_rate.py
Uses an in-memory SQLite database; does not change the original CSV files.
"""
import csv
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = ROOT / "data/retail_ops/raw/olist"
FORMAT = "%Y-%m-%d %H:%M:%S"
START, END = datetime(2018, 1, 1), datetime(2018, 2, 1)
TIME_FIELDS = (
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
)


def parse(value):
    try:
        return datetime.strptime(value, FORMAT)
    except ValueError:
        return None


def read_csv(name):
    with (RAW / f"olist_{name}_dataset.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def percentage(late, eligible):
    if not eligible:
        return None
    return str((Decimal(late) * 100 / Decimal(eligible)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)) + "%"


def main():
    manifest = json.loads((ROOT / "data/retail_ops/download_manifest.json").read_text())
    for name in ("orders", "customers"):
        filename = f"olist_{name}_dataset.csv"
        expected = next(x["sha256"] for x in manifest["files"] if x["file"] == filename)
        assert hashlib.sha256((RAW / filename).read_bytes()).hexdigest() == expected

    orders, customers = read_csv("orders"), read_csv("customers")
    assert len({o["order_id"] for o in orders}) == len(orders)
    assert len({c["customer_id"] for c in customers}) == len(customers)
    states = {c["customer_id"]: c["customer_state"] or "UNKNOWN" for c in customers}
    parsed = [{**o, **{k: parse(o[k]) for k in TIME_FIELDS}} for o in orders]
    unassigned = sum(o[TIME_FIELDS[0]] is None for o in parsed)

    # Independent Python classification: no SQL results used in these counts.
    counts = defaultdict(Counter)
    for o in parsed:
        purchased, actual, estimated = (o[k] for k in TIME_FIELDS)
        if purchased is None or not START <= purchased < END:
            continue
        c = counts[states.get(o["customer_id"], "UNKNOWN")]
        c["cohort_order_count"] += 1
        if o["order_status"] != "delivered":
            reason = "not_delivered"
        elif actual is None or estimated is None:
            reason = "invalid_delivery_time"
        elif min(actual, estimated) < purchased:
            reason = "invalid_time_order"
        else:
            reason = None
        if reason:
            c[reason] += 1
            c["excluded_order_count"] += 1
        else:
            c["eligible_order_count"] += 1
            c["late_order_count"] += actual.date() > estimated.date()

    with sqlite3.connect(":memory:") as db:
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE customers (customer_id TEXT PRIMARY KEY, customer_state TEXT)")
        db.executemany("INSERT INTO customers VALUES (?, ?)", states.items())
        db.execute("""CREATE TABLE orders (
            order_id TEXT PRIMARY KEY, customer_id TEXT, order_status TEXT,
            order_purchase_timestamp TEXT, order_delivered_customer_date TEXT,
            order_estimated_delivery_date TEXT)""")
        db.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", [
            (o["order_id"], o["customer_id"], o["order_status"],
             *(o[k].strftime(FORMAT) if o[k] else None for k in TIME_FIELDS))
            for o in parsed
        ])
        db.execute("PRAGMA query_only = ON")
        sql = (HERE / "delivered_order_late_rate_v1.sql").read_text()
        params = {"period_start": START.strftime(FORMAT),
                  "period_end": END.strftime(FORMAT), "customer_state": None}
        results = [dict(row) for row in db.execute(sql, params)]
        assert {r["customer_state"] for r in results} == set(counts)
        for r in results:
            c = counts[r["customer_state"]]
            for key in ("cohort_order_count", "eligible_order_count", "late_order_count",
                        "excluded_order_count", "not_delivered",
                        "invalid_delivery_time", "invalid_time_order"):
                assert r[key] == c[key], (r["customer_state"], key)
            expected = c["late_order_count"] / c["eligible_order_count"] if c["eligible_order_count"] else None
            assert (r["late_rate"] is None and expected is None) or (
                expected is not None and abs(r["late_rate"] - expected) <= 1e-12)
            r["late_rate_display"] = percentage(r["late_order_count"], r["eligible_order_count"])
        # Confirm a state filter and an empty period with the same reference SQL.
        sp = [dict(r) for r in db.execute(sql, {**params, "customer_state": "SP"})]
        assert len(sp) == 1 and sp[0]["cohort_order_count"] == counts["SP"]["cohort_order_count"]
        assert list(db.execute(sql, {**params, "period_start": "2026-01-01 00:00:00",
                                    "period_end": "2026-02-01 00:00:00"})) == []

    result = {
        "metric_id": "delivered_order_late_rate", "metric_version": 1,
        "parameters": params, "data_as_of": None,
        "db_snapshot": "archive_sha256:" + manifest["archive"]["sha256"],
        "contract_sha256": hashlib.sha256((ROOT / "knowledge/retail_ops/metrics/delivered_order_late_rate_v1.md").read_bytes()).hexdigest(),
        "sql_sha256": hashlib.sha256(sql.encode()).hexdigest(),
        "unassigned_purchase_time_count": unassigned,
        "verification": "SQL counts and rates match independent Python counts for all states",
        "results": results,
    }
    output = HERE / "late_rate_2018_01.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Verified {len(results)} state groups; saved {output.relative_to(ROOT)}")
    for r in results:
        if r["customer_state"] in {"SP", "RJ"}:
            print(r)


if __name__ == "__main__":
    main()
