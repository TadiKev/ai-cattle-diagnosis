# backend-django/scripts/seed_sample.py
import os
import sys

# make sure you're running from backend-django/ - otherwise adjust path
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_django.settings")  # <--- change if your settings module path differs
import django
django.setup()

from api.models import Cattle, Diagnosis, CustomUser
from api.ml_client import call_inference

def get_superuser():
    # prefer a superuser if present
    su = CustomUser.objects.filter(is_superuser=True).first()
    if su:
        return su
    # fallback: any user
    u = CustomUser.objects.first()
    return u

def create_cattle(owner):
    created = []
    for i in range(1, 11):
        tag = f"C-TST-{100+i}"
        name = f"TestCow{i}"
        c, _ = Cattle.objects.get_or_create(
            tag_number=tag,
            defaults={
                "name": name,
                "breed": "mixed",
                "age_years": 2 + (i % 6),
                "weight_kg": 200 + i * 5,
                "owner": owner
            }
        )
        created.append(c)
    return created

def seed():
    owner = get_superuser()
    if not owner:
        print("No users found. Create a user (or superuser) first: python manage.py createsuperuser")
        sys.exit(1)

    print("Using owner:", owner.username, owner.id)
    cattle = create_cattle(owner)
    print(f"Created/confirmed {len(cattle)} cattle. Total Cattle in DB:", Cattle.objects.count())

    # create diagnoses for the created cattle
    for i, c in enumerate(cattle, start=1):
        d = Diagnosis.objects.create(
            cattle=c,
            submitted_by=owner,
            symptom_text=f"auto-seed symptom {i}",
            status="pending"
        )
        # call inference; if it fails, use a mock
        try:
            resp = call_inference(symptom_text=d.symptom_text, image_paths=None, case_id=str(d.id))
        except Exception as e:
            print(f"call_inference failed for diag {d.id} (using mock): {e}")
            resp = {
                "predictions": [{"disease": "healthy", "score": 0.5}],
                "top": {"disease": "healthy", "score": 0.5},
                "confidence": 0.5,
                "explanation_text": "mock result - inference not available",
                "model_version": "mock"
            }

        d.predictions = resp.get("predictions")
        d.top_prediction = resp.get("top")
        d.confidence = float(resp.get("confidence") or resp.get("top", {}).get("score", 0.0) or 0.0)
        d.severity = resp.get("severity") or ("high" if d.confidence > 0.8 else "medium" if d.confidence > 0.5 else "low")
        d.recommendation = resp.get("explanation_text") or resp.get("recommendation", "")
        d.status = "completed"
        d.save()
        print(f"Saved diagnosis {d.id} for cattle {c.tag_number}: top={d.top_prediction} confidence={d.confidence}")

    print("Done. Totals -> Cattle:", Cattle.objects.count(), "Diagnoses:", Diagnosis.objects.count())

if __name__ == "__main__":
    seed()
