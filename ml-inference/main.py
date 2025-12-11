# ml-inference/main.py
"""
FastAPI inference server (image + optional symptom_text).
Includes:
 - normalized class_map loading (ensures index->label mapping)
 - returns human-readable labels (not numeric IDs)
 - gradcam_url uses a HTTP-served path (/gradcams/<fname>)
 - safe detach() use before numpy conversion
 - robust model load (strict/relaxed/remap attempts)
 - optional unsafe torch.load fallback controlled by env var INFERENCE_ALLOW_UNSAFE_LOAD=1
Place in ml-inference/main.py and run:
    INFERENCE_SECRET=dev-secret-please-change uvicorn main:app --host 0.0.0.0 --port 8001 --reload
"""
import os
import io
import json
import uuid
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# optional - these imports require torchvision / torch installed
try:
    import torch
    import torch.nn.functional as F
    import torchvision.transforms as T
    from torchvision.models import resnet18
    from PIL import Image
    import numpy as np
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False

log = logging.getLogger("uvicorn.error")
app = FastAPI(title="ML Inference")

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True, parents=True)

MODEL_PATH = MODELS_DIR / "best_model.pth"
CLASS_MAP_PATH = MODELS_DIR / "class_map.json"

INFERENCE_SECRET = os.getenv("INFERENCE_SECRET", "dev-secret-please-change")
# set to "1" to allow unsafe torch.load fallback (ONLY if you trust the checkpoint)
ALLOW_UNSAFE_LOAD = os.getenv("INFERENCE_ALLOW_UNSAFE_LOAD", "0") == "1"

# where to save gradcam overlays; served at /gradcams/<fname>
GRADCAM_OUT_DIR = Path(os.getenv("GRADCAM_OUT_DIR", "/mnt/data"))
GRADCAM_OUT_DIR.mkdir(parents=True, exist_ok=True)

# mount static files for gradcams so clients can fetch them
app.mount("/gradcams", StaticFiles(directory=str(GRADCAM_OUT_DIR)), name="gradcams")

# determine device if torch available
if TORCH_AVAILABLE:
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
else:
    DEVICE = "cpu"

# Globals
MODEL = None
MODEL_VERSION = "stub"
CLASS_MAP: Dict[str, str] = {}

# Image transforms (ResNet standard)
TR = None
if TORCH_AVAILABLE:
    TR = T.Compose([
        T.Resize(256),
        T.CenterCrop(224),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def load_class_map() -> Dict[str, str]:
    """
    Load class_map.json and normalize it so keys are string indices "0","1",...
    Accepts both formats:
      - {"0":"foot-and-mouth","1":"healthy",...}  (index->label)
      - {"foot-and-mouth":0,"healthy":1,...}      (label->index)  -> will invert it
    Returns mapping: {"0":"foot-and-mouth", ...}
    """
    global CLASS_MAP
    if CLASS_MAP:
        return CLASS_MAP

    if CLASS_MAP_PATH.exists():
        try:
            raw = json.loads(CLASS_MAP_PATH.read_text(encoding="utf8"))
        except Exception:
            log.exception("Failed to parse class_map.json, using default")
            raw = {}
    else:
        raw = {}

    # detect label->index form
    looks_label_to_index = False
    if isinstance(raw, dict):
        keys = list(raw.keys())
        values = list(raw.values())
        if values and any(isinstance(v, (int, float, str)) for v in values):
            if any(not str(k).isdigit() for k in keys) and any(str(v).isdigit() or isinstance(v, (int, float)) for v in values):
                looks_label_to_index = True

    normalized: Dict[str, str] = {}
    if looks_label_to_index:
        # invert
        for label, idx in raw.items():
            try:
                k = str(int(idx))
            except Exception:
                k = str(idx)
            normalized[k] = str(label)
    else:
        # assume it's index -> label already OR possibly mixed; coerce keys to string
        for k, v in raw.items():
            nk = str(k)
            normalized[nk] = str(v)

    if not normalized:
        normalized = {"0": "foot-and-mouth", "1": "healthy", "2": "lumpy"}

    CLASS_MAP = normalized
    log.info("Loaded class_map keys: %s", list(CLASS_MAP.keys()))
    return CLASS_MAP


def _is_state_dict_like(obj) -> bool:
    return isinstance(obj, dict) and all(isinstance(k, str) for k in obj.keys())


def _normalize_state_dict_keys(sd: dict) -> dict:
    """
    Heuristic remapping to make some saved keys compatible with a resnet skeleton.
    """
    new = {}
    for k, v in sd.items():
        nk = k
        if nk.startswith("module."):
            nk = nk[len("module."):]
        # remove numeric indices in classifier layers like 'fc.1.weight' -> 'fc.weight'
        nk = re.sub(r"\b(fc|classifier|head)\.\d+\.", r"\1.", nk)
        new[nk] = v
    return new


def _safe_torch_load(path: Path):
    """
    Try to load the checkpoint safely; optionally allow unsafe fallback controlled by env flag.
    """
    if not TORCH_AVAILABLE:
        raise RuntimeError("torch not available in this environment")

    last_exc = None
    try:
        return torch.load(str(path), map_location=DEVICE)
    except Exception as e:
        last_exc = e
        log.warning("Initial torch.load failed: %s", e)
        if not ALLOW_UNSAFE_LOAD:
            raise
        log.warning("ALLOW_UNSAFE_LOAD enabled; attempting torch.load(weights_only=False)")
        try:
            # NOTE: weights_only argument added in newer torch versions; attempt fallback
            return torch.load(str(path), map_location=DEVICE, weights_only=False)
        except Exception as e2:
            log.exception("Unsafe torch.load fallback failed: %s", e2)
            raise last_exc


def load_model():
    global MODEL, MODEL_VERSION
    if MODEL is not None:
        return MODEL

    if not TORCH_AVAILABLE:
        log.warning("Torch not available — inference will use stub responses")
        MODEL_VERSION = "stub"
        return None

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    class_map = load_class_map()
    num_classes = max(1, len(class_map))

    skeleton = resnet18(weights=None)
    skeleton.fc = torch.nn.Linear(skeleton.fc.in_features, num_classes)
    skeleton.to(DEVICE)

    try:
        ckpt = _safe_torch_load(MODEL_PATH)
    except Exception as e:
        log.exception("Failed to torch.load checkpoint")
        raise RuntimeError(f"Model load failed: {e}") from e

    # infer state_dict
    try:
        if hasattr(ckpt, "state_dict"):
            sd = ckpt.state_dict()
        elif isinstance(ckpt, dict) and ("state_dict" in ckpt or "model_state_dict" in ckpt):
            sd = ckpt.get("state_dict", ckpt.get("model_state_dict"))
        elif _is_state_dict_like(ckpt):
            sd = ckpt
        else:
            log.info("Checkpoint is a model object; attempting to use directly")
            ckpt.eval()
            ckpt.to(DEVICE)
            MODEL = ckpt
            MODEL_VERSION = f"module:{MODEL_PATH.name}"
            return MODEL
    except Exception as e:
        raise RuntimeError(f"Failed to interpret checkpoint: {e}") from e

    # try strict
    try:
        skeleton.load_state_dict(sd)
        skeleton.eval()
        MODEL = skeleton
        MODEL_VERSION = f"state_dict:{MODEL_PATH.name}"
        log.info("Loaded model (strict) from state_dict")
        return MODEL
    except Exception as e:
        log.warning("Strict load failed: %s", e)

    # try relaxed
    try:
        skeleton.load_state_dict(sd, strict=False)
        skeleton.eval()
        MODEL = skeleton
        MODEL_VERSION = f"state_dict_relaxed:{MODEL_PATH.name}"
        log.info("Loaded model (strict=False) from state_dict")
        return MODEL
    except Exception as e:
        log.warning("Relaxed load failed: %s", e)

    # try remapping keys
    try:
        norm_sd = _normalize_state_dict_keys(sd)
        skeleton.load_state_dict(norm_sd, strict=False)
        skeleton.eval()
        MODEL = skeleton
        MODEL_VERSION = f"state_dict_remapped:{MODEL_PATH.name}"
        log.info("Loaded model after remapping keys")
        return MODEL
    except Exception as e:
        log.exception("Remapped load failed: %s", e)

    raise RuntimeError("Model load failed after all attempts")


def prepare_image_bytes(b: bytes):
    if not TORCH_AVAILABLE:
        raise RuntimeError("Torch and PIL required for image prediction")
    return Image.open(io.BytesIO(b)).convert("RGB")


def predict_image_and_gradcam(img_pil: Image.Image, return_gradcam: bool = True) -> Dict[str, Any]:
    if not TORCH_AVAILABLE:
        log.warning("Torch not available — returning stub response")
        preds = [
            {"disease": "foot-and-mouth", "score": 0.5},
            {"disease": "lumpy", "score": 0.3},
            {"disease": "healthy", "score": 0.2},
        ]
        top = max(preds, key=lambda x: x["score"])
        return {
            "predictions": preds,
            "top": top,
            "confidence": float(top["score"]),
            "gradcam_url": None,
            "explanation_text": "Stub (torch not available).",
            "model_version": "stub",
        }

    try:
        model = load_model()
    except Exception as e:
        log.exception("Model load during predict failed")
        # fallback stub
        preds = [
            {"disease": "foot-and-mouth", "score": 0.82},
            {"disease": "lumpy", "score": 0.10},
            {"disease": "healthy", "score": 0.08},
        ]
        top = max(preds, key=lambda x: x["score"])
        return {
            "predictions": preds,
            "top": top,
            "confidence": float(top["score"]),
            "gradcam_url": None,
            "explanation_text": "Stub: model load failed on server, returning fallback.",
            "model_version": "stub",
        }

    class_map = load_class_map()
    img_tensor = TR(img_pil).unsqueeze(0).to(DEVICE)

    # find last conv layer
    target_layer = None
    for name, module in reversed(list(model.named_modules())):
        if isinstance(module, torch.nn.Conv2d):
            target_layer = module
            break

    cam_np = None
    probs = None

    if target_layer is None:
        with torch.no_grad():
            out = model(img_tensor)
            probs = F.softmax(out, dim=1).detach().cpu().numpy()[0]
    else:
        activations, gradients = {}, {}

        def forward_hook(module, inp, out):
            activations['value'] = out.detach()

        def backward_hook(module, grad_in, grad_out):
            gradients['value'] = grad_out[0].detach()

        fh = target_layer.register_forward_hook(forward_hook)
        bh = target_layer.register_full_backward_hook(backward_hook)

        model.zero_grad()
        out = model(img_tensor)

        # detach before numpy conversion to avoid "requires_grad" error
        probs = F.softmax(out, dim=1).detach().cpu().numpy()[0]

        top_idx = int(np.array(probs).argmax())
        loss = out[0, top_idx]
        loss.backward(retain_graph=False)

        act = activations.get('value')
        grad = gradients.get('value')

        try:
            fh.remove()
            bh.remove()
        except Exception:
            pass

        if act is not None and grad is not None:
            weights = grad.mean(dim=(2, 3), keepdim=True)
            cam = (weights * act).sum(dim=1, keepdim=True)
            cam = F.relu(cam)
            cam = F.interpolate(cam, size=(img_pil.height, img_pil.width), mode='bilinear', align_corners=False)
            # detach when converting to numpy
            cam = cam.squeeze().detach().cpu().numpy()
            cam = cam - cam.min()
            if cam.max() != 0:
                cam = cam / cam.max()
            cam_np = (cam * 255).astype("uint8")

    # build predictions list with human labels
    preds = []
    for i, p in enumerate(probs):
        label = class_map.get(str(i)) or class_map.get(str(i), str(i))
        preds.append({"disease": label, "score": float(p)})

    top_idx = int(np.array(probs).argmax())
    top_label = class_map.get(str(top_idx), str(top_idx))
    top = {"disease": top_label, "score": float(probs[top_idx])}

    gradcam_url = None
    if return_gradcam and cam_np is not None:
        try:
            import numpy as _np
            from PIL import Image as _Image
            heat = _Image.fromarray(_np.uint8(cam_np)).convert("L")
            heat = heat.resize(img_pil.size, resample=_Image.BILINEAR)
            heat_arr = _np.array(heat).astype(_np.uint8)
            overlay_arr = _np.zeros((img_pil.size[1], img_pil.size[0], 4), dtype=_np.uint8)
            overlay_arr[..., 0] = heat_arr
            overlay_arr[..., 3] = (heat_arr * 0.6).astype(_np.uint8)
            overlay = _Image.fromarray(overlay_arr, mode="RGBA")
            base = img_pil.convert("RGBA")
            out_img = _Image.alpha_composite(base, overlay)
            fname = f"gradcam_{uuid.uuid4().hex}.png"
            out_path = GRADCAM_OUT_DIR / fname
            out_img.convert("RGB").save(out_path, format="PNG")
            # return a client-fetchable URL path (served by StaticFiles mount)
            gradcam_url = f"/gradcams/{fname}"
        except Exception:
            log.exception("Failed to create/save gradcam")

    return {
        "predictions": preds,
        "top": top,
        "confidence": float(top["score"]),
        "gradcam_url": gradcam_url,
        "explanation_text": "Model result (local).",
        "model_version": MODEL_VERSION or "local",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
async def predict(request: Request,
                  symptom_text: str = Form(""),
                  case_id: str = Form(""),
                  file: Optional[UploadFile] = File(None)):
    secret = request.headers.get("X-Inference-Secret", "")
    if INFERENCE_SECRET and secret != INFERENCE_SECRET:
        raise HTTPException(status_code=401, detail="Bad inference secret")

    if not file:
        raise HTTPException(status_code=400, detail="No image uploaded. Provide file multipart.")

    try:
        b = await file.read()
        img = prepare_image_bytes(b)
        resp = predict_image_and_gradcam(img, return_gradcam=True)
        resp["symptom_text"] = symptom_text
        resp["case_id"] = case_id
        # Optionally, if you want full absolute URLs (convenience), you can uncomment:
        # base = f"http://{request.client.host}:{request.url.port}"
        # if resp.get("gradcam_url") and resp["gradcam_url"].startswith("/"):
        #     resp["gradcam_url"] = base + resp["gradcam_url"]
        return JSONResponse(resp)
    except FileNotFoundError as fnf:
        log.exception("Model file missing")
        raise HTTPException(status_code=503, detail=str(fnf))
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=f"prediction failed: {e}")
