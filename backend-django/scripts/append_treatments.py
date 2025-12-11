# backend-django/scripts/append_treatments.py
import json
from pathlib import Path
from api.models import Diagnosis
from django.conf import settings

def load_treatment_map():
    base = getattr(settings, "BASE_DIR", Path(__file__).resolve().parents[2])
    p = Path(base) / "metadata" / "treatment_map.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf8"))
    return {}

def extract_mg_per_kg(text):
    import re
    if not text: return None
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*mg\s*/\s*kg", text, flags=re.I)
    if m: return float(m.group(1))
    return None

def compute_dosage(weight_kg, mg_per_kg):
    try:
        total = float(weight_kg) * float(mg_per_kg)
        return f"{total:.0f} mg total ({mg_per_kg} mg/kg × {weight_kg} kg)"
    except Exception:
        return ""

tmap = load_treatment_map()
updated = 0
for d in Diagnosis.objects.all():
    top = d.top_prediction or {}
    disease = None
    if isinstance(top, dict):
        disease = top.get("disease")
    elif isinstance(top, str):
        try:
            import ast
            td = ast.literal_eval(top)
            disease = td.get("disease")
        except Exception:
            pass
    if not disease:
        continue
    treatment_text = tmap.get(disease)
    if not treatment_text:
        continue
    rec = d.recommendation or ""
    if "Suggested treatment:" not in rec:
        rec = (rec + "\n\nSuggested treatment:\n" + treatment_text).strip()
        mg = extract_mg_per_kg(treatment_text)
        if mg and getattr(d.cattle, "weight_kg", None):
            dosage = compute_dosage(d.cattle.weight_kg, mg)
            if dosage:
                rec += f"\n\nDosage guidance (auto-computed): {dosage}"
        d.recommendation = rec
        d.save(update_fields=["recommendation"])
        updated += 1

print("Updated recommendations for", updated, "diagnoses")
