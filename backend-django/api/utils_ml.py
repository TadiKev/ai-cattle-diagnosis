# api/utils_ml.py
import os
import requests
from django.core.files.base import ContentFile
from django.conf import settings
from .models import Media, Diagnosis
import logging

logger = logging.getLogger(__name__)

INFERENCE_URL = getattr(settings, "INFERENCE_URL", "http://127.0.0.1:8001/predict")
INFERENCE_SECRET = getattr(settings, "INFERENCE_SECRET", "dev-secret-please-change")

def call_inference_stub(symptom_text: str, case_id: str = None, breed=None, age=None, weight=None):
    """
    Calls the FastAPI stub and returns parsed JSON.
    """
    headers = {"X-Inference-Secret": INFERENCE_SECRET}
    data = {"symptom_text": symptom_text or "", "case_id": case_id or ""}
    r = requests.post(INFERENCE_URL, data=data, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def save_gradcam_to_media(diag: Diagnosis, gradcam_path: str):
    """
    Save a gradcam given as a local path into the Django Media model and attach to Diagnosis.
    This assumes the gradcam_path refers to a file accessible on the Django host (local fs).
    """
    try:
        if not gradcam_path:
            return None
        # if URL already (http/https) you would fetch it (requests.get) and save content.
        if gradcam_path.startswith("http://") or gradcam_path.startswith("https://"):
            # fetch remote file
            resp = requests.get(gradcam_path, timeout=20)
            resp.raise_for_status()
            content = resp.content
            fname = os.path.basename(gradcam_path)
        else:
            # treat as local path
            local_path = gradcam_path
            if not os.path.exists(local_path):
                logger.warning("Gradcam local path does not exist: %s", local_path)
                return None
            with open(local_path, "rb") as fh:
                content = fh.read()
            fname = os.path.basename(local_path)

        media = Media()
        media.file.save(fname, ContentFile(content), save=True)
        # optional: store source path in a field if you have one
        try:
            diag.images.add(media)
        except Exception:
            # fallback: if diagnosis not saved yet, you might want to save diag first
            logger.exception("Failed to attach gradcam media to diagnosis")
        return media
    except Exception:
        logger.exception("Failed to save gradcam")
        return None
