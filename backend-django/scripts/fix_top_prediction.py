# backend-django/scripts/fix_top_prediction.py
"""
Fix Diagnosis.top_prediction values that were stored as Python repr strings
(e.g. "{'disease': 'foot-and-mouth', 'score': 0.82}") and convert them to real
Python dicts (JSON-like) so your model uses JSONField properly.

This script is idempotent and will skip rows that are already dict-like.
It prints summary lines as it updates.
"""

import ast
import json
import re
from django.db import transaction
from api.models import Diagnosis

def try_parse_string_top(tp_str):
    """Try several safe ways to convert a string to a Python dict."""
    if not isinstance(tp_str, str):
        return None
    # 1) try ast.literal_eval (safe)
    try:
        val = ast.literal_eval(tp_str)
        if isinstance(val, dict):
            return val
    except Exception:
        pass
    # 2) naive single-quote -> double-quote conversion + json.loads
    try:
        s = tp_str.strip()
        # Replace unescaped single quotes with double quotes (best-effort)
        # This is conservative: it will not attempt to fix complex cases.
        s2 = re.sub(r"(?<!\\)'", '"', s)
        val = json.loads(s2)
        if isinstance(val, dict):
            return val
    except Exception:
        pass
    # 3) last resort, try to extract something that looks like key:value pairs
    try:
        # Very defensive: look for pattern like {key: value, ...}
        # We will attempt a best-effort transform: 'key': value -> "key": value and then json.loads
        s = tp_str.strip()
        s2 = s.replace("'", '"')
        val = json.loads(s2)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    return None


def main():
    total = 0
    updated = 0
    skipped = 0
    errors = 0

    qs = Diagnosis.objects.all()
    total = qs.count()
    print(f"Found {total} Diagnosis rows. Processing...")

    for d in qs.iterator():
        tp = d.top_prediction
        # if it's already a dict (or None), skip
        if tp is None:
            skipped += 1
            continue
        # In some setups top_prediction is already a dict-like (if using JSONField), test:
        if not isinstance(tp, str):
            skipped += 1
            continue

        parsed = try_parse_string_top(tp)
        if parsed is None:
            print(f"SKIP id={d.id}: could not parse top_prediction string: {tp!r}")
            errors += 1
            continue

        try:
            # Use a transaction per-row to be safe
            with transaction.atomic():
                d.top_prediction = parsed
                # If your field is JSON/text, this will write appropriate structure.
                d.save(update_fields=["top_prediction"])
            updated += 1
            print(f"UPDATED id={d.id} -> {parsed}")
        except Exception as e:
            print(f"ERROR id={d.id} saving parsed top_prediction: {e}")
            errors += 1

    print("Done.")
    print(f"Total: {total}, Updated: {updated}, Skipped (already ok / None): {skipped}, Errors/Unparsed: {errors}")


if __name__ == "__main__":
    main()
