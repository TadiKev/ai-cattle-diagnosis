# backend-django/scripts/save_gradcam.py
from pathlib import Path
from django.core.files import File
from api.models import Diagnosis, Media

GRADCAM_PATH = Path("/mnt/data/8f8836c2-e4d4-4caf-8536-bda95d776817.png")
DIAG_ID = 19

if not GRADCAM_PATH.exists():
    print("gradcam file not found:", GRADCAM_PATH)
else:
    d = Diagnosis.objects.get(pk=DIAG_ID)
    m = Media()
    with open(GRADCAM_PATH, "rb") as fh:
        m.file.save(GRADCAM_PATH.name, File(fh), save=True)
    m.gradcam_url = str(GRADCAM_PATH)  # keep original path as reference
    m.save()
    d.images.add(m)
    d.save()
    print("Saved gradcam to Media id:", m.id, "and attached to Diagnosis", DIAG_ID)
