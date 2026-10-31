"""Recompute four numeric development answers; compare SQL with Python counts.
Run from any directory: python3 evals/retail_ops/reference/build_dev_numeric_gold.py
This is a reference calculator, not a RAG/system evaluation.
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
RAW = ROOT / 'data/retail_ops/raw/olist'
FMT = '%Y-%m-%d %H:%M:%S'
START, END = datetime(2018, 1, 1), datetime(2018, 2, 1)
PARAMS = {'period_start': START.strftime(FMT), 'period_end': END.strftime(FMT), 'customer_state': None}


def parse(s):
    try:
        return datetime.strptime(s, FMT)
    except ValueError:
        return None


def cents(s):
    try:
        x = Decimal(s)
        return int(x * 100) if x.is_finite() and x >= 0 and x * 100 == (x * 100).to_integral_value() else None
    except (ArithmeticError, ValueError):
        return None


def score(s):
    return int(s) if s in {'1', '2', '3', '4', '5'} else None


def ratio(n, d):
    return n / d if d else None


def display(n, d=1, percent=False):
    if not d:
        return None
    value = Decimal(n) / Decimal(d) * (100 if percent else 1)
    return str(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) + ('%' if percent else '')


def main():
    manifest = json.loads((ROOT / 'data/retail_ops/download_manifest.json').read_text())
    tables = {}
    for name in ['orders', 'customers', 'order_items', 'order_payments', 'order_reviews']:
        path = RAW / f'olist_{name}_dataset.csv'
        expected = next(f['sha256'] for f in manifest['files'] if f['file'] == path.name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        with path.open(encoding='utf-8-sig', newline='') as f:
            tables[name] = list(csv.DictReader(f))
    orders = tables['orders']
    states = {r['customer_id']: r['customer_state'] or 'UNKNOWN' for r in tables['customers']}
    assert len(states) == len(tables['customers'])
    assert len({o['order_id'] for o in orders}) == len(orders)
    assert all(o['customer_id'] in states for o in orders)
    for table, seq in [('order_items', 'order_item_id'), ('order_payments', 'payment_sequential')]:
        assert len({(r['order_id'], r[seq]) for r in tables[table]}) == len(tables[table])
    cohort = {o['order_id']: o for o in orders if parse(o['order_purchase_timestamp']) is not None
              and START <= parse(o['order_purchase_timestamp']) < END}
    items, payments, reviews = (defaultdict(list) for _ in range(3))
    for table, grouped in [('order_items', items), ('order_payments', payments), ('order_reviews', reviews)]:
        for number, row in enumerate(tables[table], 1):
            grouped[row['order_id']].append((number, row))

    with sqlite3.connect(':memory:') as db:
        db.row_factory = sqlite3.Row
        for table, rows in tables.items():
            columns = list(rows[0])
            extras = {'order_items': ['price_cents'], 'order_payments': ['payment_value_cents'],
                      'order_reviews': ['review_score_int', 'source_row']}.get(table, [])
            defs = ', '.join('"' + c + '" ' + ('INTEGER' if c in extras else 'TEXT') for c in columns + extras)
            db.execute(f'CREATE TABLE {table} ({defs})')
            normalized = []
            for number, row in enumerate(rows, 1):
                values = []
                for column in columns:
                    v = row[column] or None
                    if column in ['order_purchase_timestamp', 'order_delivered_customer_date',
                                  'order_estimated_delivery_date', 'review_answer_timestamp']:
                        dt = parse(row[column]); v = dt.strftime(FMT) if dt else None
                    values.append(v)
                if table == 'order_items': values.append(cents(row['price']))
                if table == 'order_payments': values.append(cents(row['payment_value']))
                if table == 'order_reviews': values += [score(row['review_score']), number]
                normalized.append(values)
            db.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in columns + extras)})', normalized)
        db.execute('CREATE UNIQUE INDEX customer_key ON customers(customer_id)')
        for table in ['orders', 'order_items', 'order_payments', 'order_reviews']:
            db.execute(f'CREATE INDEX {table}_order_key ON {table}(order_id)')
        db.execute('PRAGMA query_only = ON')
        sources = {'dev014': 'delivered_order_late_rate_v1.sql', 'dev015': 'dev_item_amount.sql',
                   'dev016': 'dev_payment_amount.sql', 'dev017': 'dev_review_score.sql'}
        sql_results = {}
        for qid, filename in sources.items():
            sql_results[qid] = [dict(r) for r in db.execute((HERE / filename).read_text(), PARAMS)]
        sql_results['dev014'] = [r for r in sql_results['dev014'] if r['customer_state'] in {'SP', 'RJ'}]

    # Independently classify the raw CSV records in Python.
    late = defaultdict(Counter)
    for o in cohort.values():
        state = states[o['customer_id']]
        if state not in {'SP', 'RJ'}: continue
        c = late[state]; c['cohort_order_count'] += 1
        paid, actual, estimated = [parse(o[k]) for k in ['order_purchase_timestamp',
                                    'order_delivered_customer_date', 'order_estimated_delivery_date']]
        if o['order_status'] != 'delivered': reason = 'not_delivered'
        elif actual is None or estimated is None: reason = 'invalid_delivery_time'
        elif actual < paid or estimated < paid: reason = 'invalid_time_order'
        else: reason = None
        if reason: c[reason] += 1; c['excluded_order_count'] += 1
        else:
            c['eligible_order_count'] += 1
            c['late_order_count'] += actual.date() > estimated.date()
    py_late = []
    for state, c in sorted(late.items()):
        row = {k: c[k] for k in ['cohort_order_count', 'eligible_order_count', 'late_order_count',
               'excluded_order_count', 'not_delivered', 'invalid_delivery_time', 'invalid_time_order']}
        row.update(customer_state=state, late_rate=ratio(c['late_order_count'], c['eligible_order_count']))
        py_late.append(row)

    sp = [o for o in cohort.values() if states[o['customer_id']] == 'SP']
    delivered = [o for o in sp if o['order_status'] == 'delivered']
    amount = Decimal('0'); valid_items = contributing = missing_items = invalid_items = 0
    for o in delivered:
        rows = items[o['order_id']]; missing_items += not rows; count = 0
        for _, r in rows:
            # Fail loudly if this fixed snapshot requires a new monetary parsing decision.
            value = Decimal(r['price']); assert value.is_finite() and value >= 0 and value * 100 == int(value * 100)
            amount += value; count += 1
        valid_items += count; contributing += count > 0
    py_item = [dict(cohort_order_count=len(sp), delivered_order_count=len(delivered), valid_item_count=valid_items,
                   contributing_order_count=contributing, missing_item_order_count=missing_items,
                   invalid_item_count=invalid_items, amount_cents=int(amount * 100))]

    pay = defaultdict(lambda: {'amount': Decimal('0'), 'orders': set(), 'count': 0})
    missing_pay = sum(not payments[oid] for oid in cohort)
    for oid in cohort:
        for _, r in payments[oid]:
            value = Decimal(r['payment_value']); assert value.is_finite() and value >= 0 and value * 100 == int(value * 100)
            p = pay[r['payment_type']]; p['amount'] += value; p['orders'].add(oid); p['count'] += 1
    py_pay = [dict(payment_type=k, payment_record_count=p['count'], matched_order_count=len(p['orders']),
                   invalid_payment_count=0, amount_cents=int(p['amount'] * 100), cohort_order_count=len(cohort),
                   missing_payment_order_count=missing_pay) for k, p in sorted(pay.items())]

    rev = defaultdict(Counter)
    for oid, o in cohort.items():
        state = states[o['customer_id']]
        if state not in {'SP', 'RJ'} or o['order_status'] != 'delivered': continue
        c = rev[state]; c['target_order_count'] += 1
        candidates = [(num, r) for num, r in reviews[oid]
                      if r['review_score'] in ['1', '2', '3', '4', '5'] and parse(r['review_answer_timestamp'])]
        if not candidates:
            c['no_review_order_count' if not reviews[oid] else 'only_invalid_review_order_count'] += 1
            continue
        # Sort ascending tie-breaks first, then stable descending timestamp.
        candidates.sort(key=lambda x: (x[1]['review_id'], int(x[1]['review_score']), x[0]))
        candidates.sort(key=lambda x: parse(x[1]['review_answer_timestamp']), reverse=True)
        selected = int(candidates[0][1]['review_score'])
        c['reviewed_order_count'] += 1; c['score_sum'] += selected
        c['low_score_order_count'] += selected <= 2
        c['multiple_candidate_order_count'] += len(candidates) > 1
    py_rev = [dict(customer_state=state, **{k: c[k] for k in ['target_order_count', 'reviewed_order_count',
                'low_score_order_count', 'score_sum', 'no_review_order_count', 'only_invalid_review_order_count',
                'multiple_candidate_order_count']}) for state, c in sorted(rev.items())]
    for qid, expected in [('dev014', py_late), ('dev015', py_item), ('dev016', py_pay), ('dev017', py_rev)]:
        assert sql_results[qid] == expected, (qid, sql_results[qid], expected)

    for r in sql_results['dev014']:
        r['late_rate_display'] = display(r['late_order_count'], r['eligible_order_count'], True)
    for qid in ['dev015', 'dev016']:
        for r in sql_results[qid]: r['amount_brl_display'] = display(r['amount_cents'], 100)
    for r in sql_results['dev017']:
        for name, n, d, percent in [
            ('mean_score', r['score_sum'], r['reviewed_order_count'], False),
            ('low_score_rate', r['low_score_order_count'], r['reviewed_order_count'], True),
            ('review_coverage_rate', r['reviewed_order_count'], r['target_order_count'], True)]:
            r[name] = ratio(n, d); r[name + '_display'] = display(n, d, percent)
    payload = {'created_date': '2026-10-26', 'scope': 'full_olist_v2_snapshot',
               'db_snapshot': 'archive_sha256:' + manifest['archive']['sha256'], 'parameters': PARAMS,
               'data_as_of': None, 'verification': 'All four SQL outputs matched independent raw-CSV Python computations',
               'knowledge_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sorted((ROOT/'knowledge/retail_ops').rglob('*.md'))},
               'sql_sha256': {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in sources.values()},
               'reference_sql': sources, 'results': sql_results}
    target = HERE / 'dev_numeric_gold.json'
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print('Four numeric references verified:', target.relative_to(ROOT))
    print(json.dumps(sql_results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
