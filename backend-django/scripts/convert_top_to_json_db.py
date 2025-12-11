# scripts/convert_top_to_json_db.py
"""
Convert existing api_diagnosis.top_prediction values (Python repr strings)
into valid JSON text so SQLite's JSON_VALID check passes during migration.
"""

import os
import django
import ast
import json
import re
from django.conf import settings
import sqlite3

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cattle_diag.settings")  # adjust if your settings module differs
django.setup()

DB_PATH = settings.DATABASES["default"]["NAME"]
print("Using DB:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

rows = cur.execute("SELECT id, top_prediction FROM api_diagnosis").fetchall()
print(f"Found {len(rows)} rows in api_diagnosis")

updated = 0
skipped = 0

for row in rows:
    pk, tp = row
    if tp is None:
        skipped += 1
        continue
    if not isinstance(tp, str):
        skipped += 1
        continue

    parsed = None
    # 1) try ast.literal_eval (handles Python dict repr)
    try:
        parsed = ast.literal_eval(tp)
    except Exception:
        parsed = None

    # 2) fallback: convert single quotes -> double quotes, attempt json.loads
    if parsed is None:
        try:
            s = tp.strip()
            # best-effort replace unescaped single quotes with double quotes
            s2 = re.sub(r"(?<!\\)'", '"', s)
            # normalize Python literals to JSON
            s2 = re.sub(r"\bNone\b", "null", s2)
            s2 = re.sub(r"\bTrue\b", "true", s2)
            s2 = re.sub(r"\bFalse\b", "false", s2)
            parsed = json.loads(s2)
        except Exception:
            parsed = None

    # 3) last resort: naive replace then json.loads
    if parsed is None:
        try:
            s3 = tp.replace("'", '"')
            parsed = json.loads(s3)
        except Exception:
            parsed = None

    if parsed is None:
        print(f"SKIP id={pk}: could not parse -> {tp!r}")
        skipped += 1
        continue

    # ensure parsed is dict/list
    if not isinstance(parsed, (dict, list)):
        print(f"SKIP id={pk}: parsed to {type(parsed).__name__}, not dict/list")
        skipped += 1
        continue

    json_text = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
    cur.execute("UPDATE api_diagnosis SET top_prediction = ? WHERE id = ?", (json_text, pk))
    updated += 1
    print(f"UPDATED id={pk} -> {json_text}")

conn.commit()
conn.close()
print(f"Done. updated={updated}, skipped={skipped}")
