# backend-django/api/views.py
import os
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import viewsets, status, generics, permissions, filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.decorators import action

from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Cattle, Diagnosis, Media, CustomUser, DiagnosisAudit
from .serializers import (
    CattleSerializer,
    DiagnosisSerializer,
    MediaSerializer,
    UserSerializer,
    DiagnosisReviewSerializer,  # <--- ensure review serializer is imported
)
from .permissions import IsOwnerOrVetAdmin, IsVetOrAdmin
from .ml_client import call_inference, download_gradcam_image, SAMPLE_GRADCAM_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Treatment map loader (memoized) — tolerate BOM using utf-8-sig
# ---------------------------------------------------------------------------
_TREATMENT_MAP: Optional[Dict[str, str]] = None


def load_treatment_map() -> Dict[str, str]:
    global _TREATMENT_MAP
    if _TREATMENT_MAP is not None:
        return _TREATMENT_MAP

    base = getattr(settings, "BASE_DIR", None)
    if not base:
        base = Path(__file__).resolve().parents[2]
    p = Path(base) / "metadata" / "treatment_map.json"
    if p.exists():
        try:
            _TREATMENT_MAP = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            logger.exception("Failed to parse treatment_map.json at %s: %s", p, exc)
            _TREATMENT_MAP = {}
    else:
        _TREATMENT_MAP = {}
    return _TREATMENT_MAP


# ---------------------------------------------------------------------------
# Dosage helpers
# ---------------------------------------------------------------------------
def compute_dosage(weight_kg: float, mg_per_kg: float) -> str:
    try:
        total_mg = float(weight_kg) * float(mg_per_kg)
        return f"{total_mg:.0f} mg total ({mg_per_kg} mg/kg × {weight_kg} kg)"
    except Exception:
        return ""


def _extract_mg_per_kg(treatment_text: str) -> Optional[float]:
    if not treatment_text:
        return None
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*mg\s*/\s*kg", treatment_text, flags=re.I)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    m = re.search(r"mg[_\s/]*per[_\s]*kg[:=]?\s*([0-9]+(?:\.[0-9]+)?)", treatment_text, flags=re.I)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    m = re.search(r"mg_per_kg[:=]\s*([0-9]+(?:\.[0-9]+)?)", treatment_text, flags=re.I)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Lightweight ML response postprocessing
# ---------------------------------------------------------------------------
DISEASE_KEYWORDS = {
    "foot-and-mouth": ["mouth", "ulcer", "saliva", "drool", "blister", "lesion"],
    "lumpy": ["lump", "bump", "swelling", "nodul", "lumpy"],
    "healthy": ["no sign", "healthy", "normal", "none"],
}

DEFAULT_ML_TEMP = float(getattr(settings, "ML_TEMP", 1.0))
BOOST_FACTOR = float(getattr(settings, "ML_KEYWORD_BOOST", 0.18))
UNCERTAINTY_THRESHOLD = float(getattr(settings, "ML_UNCERTAINTY_THRESHOLD", 0.5))


def _apply_temperature_scaling(probs: List[float], temp: float = 1.0) -> List[float]:
    import numpy as _np

    if temp is None or float(temp) == 1.0:
        return probs
    arr = _np.array(probs, dtype=_np.float64)
    arr = _np.clip(arr, 1e-12, 1.0)
    logits = _np.log(arr)
    scaled = _np.exp(logits / float(temp))
    scaled = scaled / float(_np.sum(scaled))
    return scaled.tolist()


def _boost_by_keywords(preds: List[Dict], symptom_text: str) -> List[Dict]:
    txt = (symptom_text or "").lower()
    boosts = {}
    for disease, kws in DISEASE_KEYWORDS.items():
        for kw in kws:
            if kw in txt:
                boosts[disease] = boosts.get(disease, 0.0) + BOOST_FACTOR
    scores = []
    for p in preds:
        base = float(p.get("score", 0.0))
        addition = boosts.get(p.get("disease"), 0.0)
        scores.append((p.get("disease"), base + addition))
    total = sum(s for _, s in scores) or 1.0
    return [{"disease": d, "score": s / total} for d, s in scores]


def postprocess_ml_response(resp: Dict[str, Any], symptom_text: str = "", cattle: Optional[Cattle] = None) -> Dict[str, Any]:
    out = dict(resp)
    raw_preds = resp.get("predictions", []) or []
    diseases = [p.get("disease") for p in raw_preds]
    scores = [float(p.get("score", 0.0)) for p in raw_preds]

    # temperature scaling
    scaled = _apply_temperature_scaling(scores, DEFAULT_ML_TEMP)
    preds = [{"disease": d, "score": s} for d, s in zip(diseases, scaled)]

    # keyword boost
    preds_boosted = _boost_by_keywords(preds, symptom_text)

    # optional cattle-based heuristics (small example)
    if cattle:
        try:
            w = getattr(cattle, "weight_kg", None)
            if w is not None:
                w = float(w)
                for p in preds_boosted:
                    if p["disease"] == "lumpy" and w < 40:
                        p["score"] *= 0.9
        except Exception:
            pass

    # renormalize
    total = sum(p["score"] for p in preds_boosted) or 1.0
    preds_final = [{"disease": p["disease"], "score": float(p["score"] / total)} for p in preds_boosted]

    top = max(preds_final, key=lambda x: x["score"]) if preds_final else None
    confidence = top["score"] if top else 0.0
    uncertain = confidence < UNCERTAINTY_THRESHOLD

    recommendation_suffix = ""
    if uncertain:
        recommendation_suffix = ("\n\nNote: Model confidence is low. Consider consulting a veterinarian and uploading additional images or symptom details.")

    out["predictions_raw"] = raw_preds
    out["predictions_processed"] = preds_final
    out["top_processed"] = top
    out["confidence_processed"] = float(confidence)
    out["uncertain"] = bool(uncertain)
    out["recommendation_suffix"] = recommendation_suffix
    return out


# ---------------------------------------------------------------------------
# Auth endpoints (unchanged)
# ---------------------------------------------------------------------------
class RegisterView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer


class LoginView(TokenObtainPairView):
    permission_classes = (permissions.AllowAny,)


class MeView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


# ---------------------------------------------------------------------------
# CattleViewSet
# ---------------------------------------------------------------------------
class CattleViewSet(viewsets.ModelViewSet):
    serializer_class = CattleSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwnerOrVetAdmin)
    filter_backends = (filters.SearchFilter,)
    search_fields = ("tag_number", "name", "breed")

    def get_queryset(self):
        user = self.request.user
        if user.role in ("vet", "admin") or user.is_superuser:
            return Cattle.objects.all()
        return Cattle.objects.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


# ---------------------------------------------------------------------------
# DiagnosisViewSet (create + review)
# ---------------------------------------------------------------------------
class DiagnosisViewSet(viewsets.ModelViewSet):
    serializer_class = DiagnosisSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwnerOrVetAdmin)
    # add JSONParser so endpoints accept application/json from frontend (review modal)
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filter_backends = (filters.SearchFilter,)
    search_fields = ("top_prediction", "severity", "status")
    queryset = Diagnosis.objects.select_related("cattle", "submitted_by").prefetch_related("images").all()


    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        cattle_id = self.request.query_params.get("cattle_id")
        if cattle_id:
            qs = qs.filter(cattle__id=cattle_id)
        if user.role in ("vet", "admin") or user.is_superuser:
            return qs
        return qs.filter(Q(submitted_by=user) | Q(cattle__owner=user))

    def _resolve_gradcam_candidates(self, gradcam_url: str) -> List[str]:
        candidates: List[str] = []
        if not gradcam_url:
            return candidates

        candidates.append(gradcam_url)
        base = getattr(settings, "BASE_DIR", None)
        if not base:
            base = Path(__file__).resolve().parents[2]

        p = Path(gradcam_url)
        if gradcam_url.startswith("/"):
            candidates.append(str(Path(base) / gradcam_url.lstrip("/")))
            candidates.append(str(Path(base) / "ml-inference" / gradcam_url.lstrip("/")))
            candidates.append(str(Path(base) / "ml-inference" / "gradcams" / p.name))
            candidates.append(str(Path(base) / "gradcams" / p.name))
            candidates.append(str(Path(base) / "backend-django" / "gradcams" / p.name))
        else:
            candidates.append(str(Path(base) / "ml-inference" / p.name))
            candidates.append(str(Path(base) / "gradcams" / p.name))
            candidates.append(str(Path(base) / p.name))

        if SAMPLE_GRADCAM_PATH:
            candidates.append(str(SAMPLE_GRADCAM_PATH))

        seen = set()
        dedup = []
        for c in candidates:
            if c and c not in seen:
                dedup.append(c)
                seen.add(c)
        return dedup

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        cattle = validated.get("cattle")
        symptom_text = validated.get("symptom_text", "")

        # collect uploaded files
        uploaded_files = []
        if "uploaded_images" in request.FILES:
            uploaded_files = request.FILES.getlist("uploaded_images")
        elif "image" in request.FILES:
            uploaded_files = request.FILES.getlist("image")
        else:
            uploaded_files = list(request.FILES.values())

        with transaction.atomic():
            diag = Diagnosis.objects.create(
                cattle=cattle,
                submitted_by=request.user,
                symptom_text=symptom_text,
                status="pending"
            )

            image_paths: List[str] = []
            for f in uploaded_files:
                media = Media.objects.create(file=f)
                diag.images.add(media)
                try:
                    if hasattr(media.file, "path") and media.file.path:
                        image_paths.append(media.file.path)
                except Exception:
                    logger.warning("Media file has no .path (maybe remote storage): %s", getattr(media.file, "name", None))

            # call inference
            try:
                resp = call_inference(
                    symptom_text=diag.symptom_text or "",
                    image_paths=image_paths or None,
                    breed=(diag.cattle.breed if diag.cattle else None),
                    age=(diag.cattle.age_years if diag.cattle else None),
                    weight=(diag.cattle.weight_kg if diag.cattle else None),
                    case_id=str(diag.id)
                )
            except Exception as exc:
                logger.exception("Inference call failed: %s", exc)
                diag.status = "failed"
                diag.recommendation = "Inference call failed. Please retry."
                diag.save()
                out = DiagnosisSerializer(diag, context={"request": request})
                return Response(out.data, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            # Postprocess ML response
            resp_processed = postprocess_ml_response(resp, symptom_text=diag.symptom_text, cattle=diag.cattle)

            # Save processed fields
            try:
                diag.predictions = resp_processed.get("predictions_processed") or resp.get("predictions")
                diag.top_prediction = resp_processed.get("top_processed") or resp.get("top")
                diag.confidence = float(resp_processed.get("confidence_processed") or resp.get("confidence") or 0.0)
            except Exception:
                logger.exception("Failed to write predictions to Diagnosis model")

            # severity
            severity = resp.get("severity")
            if not severity:
                c = diag.confidence or 0.0
                if c > 0.8:
                    severity = "high"
                elif c > 0.5:
                    severity = "medium"
                else:
                    severity = "low"
            diag.severity = severity

            # base recommendation
            rec = resp.get("explanation_text") or resp.get("recommendation") or ""
            if not rec:
                top = diag.top_prediction or {}
                if top:
                    rec = f"Top prediction: {top.get('disease')} (score {top.get('score')}). Consult a veterinarian for confirmation."

            # append treatment from treatment_map.json
            try:
                top = resp_processed.get("top_processed") or resp.get("top") or {}
                disease_label = (top.get("disease") if isinstance(top, dict) else None)
                if disease_label:
                    treatment_map = load_treatment_map()
                    treatment_text = treatment_map.get(disease_label)
                    if treatment_text:
                        rec = (rec or "") + "\n\nSuggested treatment:\n" + treatment_text
                        mg_per_kg = _extract_mg_per_kg(treatment_text)
                        weight_val = getattr(diag.cattle, "weight_kg", None) if diag.cattle else None
                        if mg_per_kg and weight_val:
                            dosage = compute_dosage(weight_val, mg_per_kg)
                            if dosage:
                                rec += f"\n\nDosage guidance (auto-computed): {dosage}"
            except Exception:
                logger.exception("Failed to append treatment_map info")

            # append recommendation_suffix from processed (e.g. low-confidence note)
            rec = (rec or "") + (resp_processed.get("recommendation_suffix") or "")

            diag.recommendation = rec

            # handle gradcam_url (try multiple candidate paths/URLs)
            gradcam_url = resp.get("gradcam_url") or resp_processed.get("gradcam_url")
            saved_gradcam = False
            if gradcam_url:
                try:
                    candidates = self._resolve_gradcam_candidates(str(gradcam_url))
                    for cand in candidates:
                        try:
                            content = download_gradcam_image(cand)
                            if content:
                                fname = f"gradcam_{diag.id}_{os.path.basename(cand)}"
                                media = Media()
                                media.file.save(fname, ContentFile(content), save=True)
                                try:
                                    media.gradcam_url = cand
                                    media.save()
                                except Exception:
                                    media.save()
                                diag.images.add(media)
                                saved_gradcam = True
                                logger.info("Saved gradcam from candidate: %s", cand)
                                break
                        except Exception:
                            logger.debug("Candidate failed for gradcam: %s", cand, exc_info=True)
                except Exception:
                    logger.exception("Failed to download/save gradcam")

            # dev fallback: save sample gradcam if none saved
            if not saved_gradcam:
                try:
                    if SAMPLE_GRADCAM_PATH and os.path.exists(SAMPLE_GRADCAM_PATH):
                        content = download_gradcam_image(str(SAMPLE_GRADCAM_PATH))
                        if content:
                            fname = f"gradcam_{diag.id}_{os.path.basename(SAMPLE_GRADCAM_PATH)}"
                            media = Media()
                            media.file.save(fname, ContentFile(content), save=True)
                            try:
                                media.gradcam_url = SAMPLE_GRADCAM_PATH
                                media.save()
                            except Exception:
                                media.save()
                            diag.images.add(media)
                            saved_gradcam = True
                except Exception:
                    logger.exception("Failed to save sample gradcam fallback")

            diag.status = "completed"
            diag.save()

        out = DiagnosisSerializer(Diagnosis.objects.get(pk=diag.pk), context={"request": request}).data
        out["_ml"] = {
            "predictions_raw": resp.get("predictions"),
            "predictions_processed": resp_processed.get("predictions_processed"),
            "top_processed": resp_processed.get("top_processed"),
            "confidence_processed": resp_processed.get("confidence_processed"),
            "uncertain": resp_processed.get("uncertain"),
            "model_version": resp.get("model_version") or resp_processed.get("model_version"),
        }
        return Response(out, status=status.HTTP_201_CREATED)

    # ------------------ Review action (vets/admins only) ------------------
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsVetOrAdmin])
    def review(self, request, pk=None):
        """
        Veterinary review endpoint:
          POST /api/diagnosis/{id}/review/
        Payload: DiagnosisReviewSerializer (review_status, review_notes, optional overrides)
        """
        diag = self.get_object()

        # Validate incoming payload
        serializer = DiagnosisReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Snapshot before
        before = {
            "predictions": diag.predictions,
            "top_prediction": diag.top_prediction,
            "confidence": diag.confidence,
            "recommendation": diag.recommendation,
            "status": diag.status,
            "review_status": diag.review_status,
            "review_notes": diag.review_notes,
        }

        # Apply review changes
        diag.review_status = data.get("review_status", diag.review_status)
        diag.review_notes = data.get("review_notes", diag.review_notes)
        diag.reviewed_by = request.user
        diag.reviewed_at = timezone.now()

        # Optional overrides from vet
        if "predictions" in data and data["predictions"] is not None:
            diag.predictions = data["predictions"]
        if "top_prediction" in data and data["top_prediction"] is not None:
            diag.top_prediction = data["top_prediction"]
        if "recommendation" in data and data["recommendation"] is not None:
            diag.recommendation = data["recommendation"]

        # decide status mapping
        if diag.review_status == "approved":
            diag.status = "completed"
        elif diag.review_status == "rejected":
            diag.status = "rejected"
        else:
            # edited
            diag.status = "under_treatment" if diag.severity == "medium" else diag.status

        diag.save()

        # Create audit record
        try:
            DiagnosisAudit.objects.create(
                diagnosis=diag,
                actor=request.user,
                action=diag.review_status,
                before=before,
                after={
                    "predictions": diag.predictions,
                    "top_prediction": diag.top_prediction,
                    "confidence": diag.confidence,
                    "recommendation": diag.recommendation,
                    "status": diag.status,
                    "review_status": diag.review_status,
                    "review_notes": diag.review_notes,
                },
                notes=diag.review_notes or "",
            )
        except Exception:
            logger.exception("Failed to create DiagnosisAudit for review")

        out = DiagnosisSerializer(diag, context={"request": request}).data
        return Response(out, status=status.HTTP_200_OK)
