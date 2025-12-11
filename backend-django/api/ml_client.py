# backend-django/api/ml_client.py
"""
Robust ML client used by Django:
 - call_inference(...) -> dict (posts to settings.INFERENCE_URL)
 - download_gradcam_image(url) -> bytes|None (tries many fallbacks)
Place this file at backend-django/api/ml_client.py and restart Django.
"""
import os
import logging
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# dev fallback gradcam (unchanged)
SAMPLE_GRADCAM_PATH = getattr(settings, "SAMPLE_GRADCAM_PATH", "/mnt/data/8f8836c2-e4d4-4caf-8536-bda95d776817.png")


def _is_http_url(p: str) -> bool:
    try:
        s = urlparse(p).scheme
        return s in ("http", "https")
    except Exception:
        return False


def _is_file_uri(p: str) -> bool:
    try:
        return urlparse(p).scheme == "file"
    except Exception:
        return False


def _gather_candidate_paths(url: str) -> List[str]:
    """
    Return a list of local filesystem candidate paths to try reading the gradcam from.
    This covers Unix-style names ("/gradcams/..", "/mnt/data/..."), Windows absolute paths,
    the repo's ml-inference/gradcams, repo gradcams, and a sample fallback.
    """
    candidates: List[str] = []
    if not url:
        return candidates

    # Normalize separators
    url_norm = url.replace("\\", "/").strip()

    # Project base: settings.BASE_DIR if available, otherwise two parents up from this file
    base = getattr(settings, "BASE_DIR", None)
    if base:
        base = Path(base)
    else:
        # go up two levels: backend-django/
        base = Path(__file__).resolve().parents[2]

    # If URL looks like Windows absolute path (starts with drive letter)
    # pathlib.Path.is_absolute handles Windows absolute paths correctly.
    try:
        p_obj = Path(url)
        if p_obj.is_absolute():
            candidates.append(str(p_obj))
            # Also include the normalized form with forward slashes
            candidates.append(str(Path(url_norm)))
    except Exception:
        pass

    # Common ML server outputs (unix-like)
    if url_norm.startswith("/"):
        # project-root relative (strip leading slash)
        candidates.append(str(base / url_norm.lstrip("/")))
        # ml-inference/gradcams/<name>
        candidates.append(str(base / "ml-inference" / url_norm.lstrip("/")))
        candidates.append(str(base / "ml-inference" / "gradcams" / Path(url_norm).name))
        candidates.append(str(base / "gradcams" / Path(url_norm).name))
        candidates.append(str(base / "backend-django" / "gradcams" / Path(url_norm).name))
    else:
        # not starting with slash - try likely locations
        candidates.append(str(base / "ml-inference" / Path(url_norm).name))
        candidates.append(str(base / "gradcams" / Path(url_norm).name))
        candidates.append(str(base / Path(url_norm).name))
        candidates.append(str(Path(url_norm)))  # raw value (useful for Windows backslash form)

    # add SAMPLE_GRADCAM_PATH last-resort
    if SAMPLE_GRADCAM_PATH:
        candidates.append(str(SAMPLE_GRADCAM_PATH))

    # Deduplicate preserving order
    seen = set()
    dedup = []
    for c in candidates:
        if not c:
            continue
        if c not in seen:
            dedup.append(c)
            seen.add(c)
    return dedup


def call_inference(
    symptom_text: str,
    image_paths: Optional[List[str]] = None,
    breed: Optional[str] = None,
    age: Optional[float] = None,
    weight: Optional[float] = None,
    case_id: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Post to settings.INFERENCE_URL and return parsed JSON.

    - Attaches local files from image_paths if they exist.
    - Sends remote URLs (http/https) as CSV in 'image_urls'.
    - If request fails and INFERENCE_ALLOW_FALLBACK True, returns stub response.
    """
    url = getattr(settings, "INFERENCE_URL", "http://127.0.0.1:8001/predict")
    secret = getattr(settings, "INFERENCE_SECRET", "dev-secret-please-change")
    allow_fallback = getattr(settings, "INFERENCE_ALLOW_FALLBACK", True)

    headers = {"X-Inference-Secret": secret} if secret else {}

    data: Dict[str, Any] = {
        "symptom_text": symptom_text or "",
        "breed": breed or "",
        "age": "" if age is None else str(age),
        "weight": "" if weight is None else str(weight),
        "case_id": case_id or "",
    }

    opened = []
    files_arg = None

    try:
        if image_paths:
            files = []
            remote_urls = []
            for p in image_paths:
                if not p:
                    continue
                if _is_http_url(p):
                    remote_urls.append(p)
                    continue
                # attach local file if exists
                try:
                    # prefer absolute check
                    if os.path.isabs(p) and os.path.exists(p):
                        fh = open(p, "rb")
                        opened.append(fh)
                        mtype, _ = mimetypes.guess_type(p)
                        files.append(("file", (os.path.basename(p), fh, mtype or "application/octet-stream")))
                    else:
                        # try resolving relative path
                        possible = os.path.abspath(p)
                        if os.path.exists(possible):
                            fh = open(possible, "rb")
                            opened.append(fh)
                            mtype, _ = mimetypes.guess_type(possible)
                            files.append(("file", (os.path.basename(possible), fh, mtype or "application/octet-stream")))
                        else:
                            logger.debug("call_inference: image path not found locally: %s", p)
                except Exception:
                    logger.exception("call_inference: failed to attach %s", p)
            files_arg = files if files else None
            if remote_urls:
                data["image_urls"] = ",".join(remote_urls)

        if files_arg:
            resp = requests.post(url, headers=headers, data=data, files=files_arg, timeout=timeout)
        else:
            resp = requests.post(url, headers=headers, data=data, timeout=timeout)

        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.exception("call_inference request failed: %s (url=%s)", e, url)
        if not allow_fallback:
            raise
        # dev fallback stub
        return {
            "predictions": [
                {"disease": "foot-and-mouth", "score": 0.82},
                {"disease": "lumpy", "score": 0.10},
                {"disease": "healthy", "score": 0.08},
            ],
            "top": {"disease": "foot-and-mouth", "score": 0.82},
            "confidence": 0.82,
            "gradcam_url": SAMPLE_GRADCAM_PATH,
            "explanation_text": "Stub: highlighted important regions (mock).",
            "model_version": "v0.0.1-stub",
        }
    finally:
        for fh in opened:
            try:
                fh.close()
            except Exception:
                logger.exception("Failed closing file handle")


def download_gradcam_image(url: str, timeout: int = 20) -> Optional[bytes]:
    """
    Robustly try to obtain bytes for a gradcam_url.
    Order of attempts:
      1) HTTP(S) GET if url looks like http(s)
      2) file:// -> local open
      3) os.path.isabs(url) -> open directly
      4) try project-relative candidate paths (via _gather_candidate_paths)
      5) try to fetch from inference server: INFERENCE_PUBLIC_BASE or INFERENCE_URL (strip /predict) + url OR /gradcams/<basename>
      6) return None
    Extensive logging included to help debug missing files.
    """
    if not url:
        return None

    url_str = str(url).strip()
    url_norm = url_str.replace("\\", "/")

    logger.debug("download_gradcam_image: requested url=%s", url_str)

    # 1) HTTP(S)
    if _is_http_url(url_str):
        try:
            r = requests.get(url_str, timeout=timeout)
            r.raise_for_status()
            logger.info("download_gradcam_image: fetched http url %s", url_str)
            return r.content
        except Exception:
            logger.exception("download_gradcam_image: failed http fetch %s", url_str)
            # fall through to other attempts

    # 2) file://
    if _is_file_uri(url_norm):
        parsed = urlparse(url_norm)
        local_path = parsed.path
        try:
            if os.path.exists(local_path):
                with open(local_path, "rb") as fh:
                    logger.info("download_gradcam_image: read file:// path %s", local_path)
                    return fh.read()
            logger.warning("download_gradcam_image: file:// path not found %s", local_path)
        except Exception:
            logger.exception("download_gradcam_image: failed reading file:// path %s", local_path)

    # 3) absolute path direct (handles Windows drive letters)
    try:
        if os.path.isabs(url_str) or os.path.isabs(url_norm):
            direct = url_str if os.path.isabs(url_str) else url_norm
            try:
                if os.path.exists(direct):
                    with open(direct, "rb") as fh:
                        logger.info("download_gradcam_image: read absolute path %s", direct)
                        return fh.read()
            except Exception:
                logger.exception("download_gradcam_image: failed reading absolute path %s", direct)
    except Exception:
        logger.debug("download_gradcam_image: exception while checking absolute path", exc_info=True)

    # 4) candidate local paths
    try:
        candidates = _gather_candidate_paths(url_norm)
        logger.debug("download_gradcam_image: candidate local paths: %s", candidates)
        for cand in candidates:
            try:
                if os.path.exists(cand):
                    with open(cand, "rb") as fh:
                        logger.info("download_gradcam_image: found candidate file %s", cand)
                        return fh.read()
                else:
                    logger.debug("download_gradcam_image: candidate does not exist %s", cand)
            except Exception:
                logger.debug("download_gradcam_image: candidate open failed %s", cand, exc_info=True)
    except Exception:
        logger.exception("download_gradcam_image: failed gathering/trying candidate paths for %s", url_norm)

    # 5) attempt to fetch from inference server using INFERENCE_PUBLIC_BASE or INFERENCE_URL
    try:
        # Prefer configured public base (full scheme + host)
        public_base = getattr(settings, "INFERENCE_PUBLIC_BASE", None)
        inference_url = getattr(settings, "INFERENCE_URL", None)
        base_to_try = public_base or inference_url

        if base_to_try:
            # strip "/predict" if present (common)
            base = base_to_try.rstrip("/")
            if base.endswith("/predict"):
                base = base[: -len("/predict")]

            # If url starts with '/', join directly; otherwise try /gradcams/<basename>
            http_candidates = []
            if url_norm.startswith("/"):
                http_candidates.append(base + url_norm)
                # also try base + '/gradcams/' + basename
                http_candidates.append(base + "/gradcams/" + Path(url_norm).name)
            else:
                # try base + '/gradcams/' + basename
                http_candidates.append(base + "/gradcams/" + Path(url_norm).name)
                # also base + '/' + url_norm
                http_candidates.append(base + "/" + url_norm)

            # remove duplicates while preserving order
            seen = set()
            http_candidates_clean = []
            for h in http_candidates:
                if h not in seen:
                    http_candidates_clean.append(h)
                    seen.add(h)

            logger.debug("download_gradcam_image: trying inference-server HTTP candidates: %s", http_candidates_clean)
            for hc in http_candidates_clean:
                try:
                    r = requests.get(hc, timeout=timeout)
                    if r.status_code == 200 and r.content:
                        logger.info("download_gradcam_image: fetched from inference server %s", hc)
                        return r.content
                    else:
                        logger.debug("download_gradcam_image: inference-server returned %s for %s", r.status_code, hc)
                except Exception:
                    logger.debug("download_gradcam_image: failed http fetch %s", hc, exc_info=True)
    except Exception:
        logger.exception("download_gradcam_image: error while trying inference-server fetch for %s", url_norm)

    logger.warning("download_gradcam_image: Unsupported gradcam_url scheme or couldn't locate file: %s", url_str)
    return None
