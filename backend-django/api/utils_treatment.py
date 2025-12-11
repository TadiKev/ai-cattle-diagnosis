# api/utils_treatment.py
from pathlib import Path
import json
from django.conf import settings

TREATMENT_MAP = None
def load_treatment_map():
    global TREATMENT_MAP
    if TREATMENT_MAP is None:
        p = Path(settings.BASE_DIR) / "metadata" / "treatment_map.json"
        if p.exists():
            TREATMENT_MAP = json.loads(p.read_text(encoding="utf8"))
        else:
            TREATMENT_MAP = {}
    return TREATMENT_MAP

def compute_dosage(weight_kg, mg_per_kg):
    try:
        w = float(weight_kg)
    except (TypeError, ValueError):
        return None
    total_mg = mg_per_kg * w
    return f"{total_mg:.0f} mg total ({mg_per_kg} mg/kg × {w} kg)"
