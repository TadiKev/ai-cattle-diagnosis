# backend-django/api/management/commands/seed_sample.py
from django.core.management.base import BaseCommand
from api.models import Cattle, Diagnosis, CustomUser
from api.ml_client import call_inference
import sys

class Command(BaseCommand):
    help = "Seed sample cattle and diagnoses (10 each)."

    def handle(self, *args, **options):
        owner = CustomUser.objects.filter(is_superuser=True).first() or CustomUser.objects.first()
        if not owner:
            self.stdout.write(self.style.ERROR("No user found. Run createsuperuser first."))
            sys.exit(1)

        self.stdout.write(f"Using owner: {owner.username} ({owner.id})")
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

        self.stdout.write(self.style.SUCCESS(f"Created/confirmed {len(created)} cattle."))

        for i, c in enumerate(created, start=1):
            d = Diagnosis.objects.create(cattle=c, submitted_by=owner, symptom_text=f"auto-seed symptom {i}", status="pending")
            try:
                resp = call_inference(symptom_text=d.symptom_text, image_paths=None, case_id=str(d.id))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"call_inference failed for {d.id}, using mock: {e}"))
                resp = {"predictions":[{"disease":"healthy","score":0.5}], "top":{"disease":"healthy","score":0.5}, "confidence":0.5, "explanation_text":"mock"}

            d.predictions = resp.get("predictions")
            d.top_prediction = resp.get("top")
            d.confidence = float(resp.get("confidence") or resp.get("top", {}).get("score", 0.0) or 0.0)
            d.severity = resp.get("severity") or ("high" if d.confidence>0.8 else "medium" if d.confidence>0.5 else "low")
            d.recommendation = resp.get("explanation_text") or resp.get("recommendation","")
            d.status = "completed"
            d.save()
            self.stdout.write(self.style.SUCCESS(f"Saved diagnosis {d.id} for {c.tag_number}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Totals -> Cattle: {Cattle.objects.count()} Diagnoses: {Diagnosis.objects.count()}"))
