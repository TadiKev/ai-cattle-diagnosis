from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from PIL import Image
import os, io, uuid, numpy as np

# Lazy model placeholder
_model = None
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v0.1.0")
INFERENCE_SECRET = os.environ.get("INFERENCE_SECRET", "change-me")

app = FastAPI(title="AI Cattle Inference")

# CORS - allow all for dev, restrict in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static gradcam images
MEDIA_DIR = "/app/media"
GRADCAM_DIR = os.path.join(MEDIA_DIR, "gradcams")
os.makedirs(GRADCAM_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


def check_secret(val: Optional[str]):
    if val != INFERENCE_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health/")
async def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


def _lazy_load_model():
    global _model
    if _model is None:
        # Placeholder: load your actual model(s) here
        _model = {"loaded": True, "name": "dummy-model"}
    return _model


def _process_image_bytes(file_bytes: bytes, target_size=(224,224)):
    # Validate and preprocess image
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img = img.resize(target_size)
    arr = np.array(img).astype(np.float32) / 255.0
    # shape (H,W,3) -> (1, H, W, 3)
    return np.expand_dims(arr, 0)


@app.post("/predict/")
async def predict(
    symptom_text: Optional[str] = Form(None),
    breed: Optional[str] = Form(None),
    age: Optional[str] = Form(None),
    weight: Optional[str] = Form(None),
    case_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    inference_secret: Optional[str] = Header(None, convert_underscores=False, alias="INFERENCE_SECRET")
):
    # Security
    check_secret(inference_secret)

    # Lazy-load model
    model = _lazy_load_model()

    predictions: List[Dict[str, Any]] = []

    # If image present: validate size and MIME
    gradcam_url = None
    if image:
        content = await image.read()
        # max 10MB
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
        mime = image.content_type or ""
        if not mime.startswith("image/"):
            raise HTTPException(status_code=400, detail="Uploaded file is not an image")
        # preprocess (dummy)
        inp = _process_image_bytes(content, target_size=(224,224))
        # dummy image prediction
        predictions.append({"disease": "Bovine Respiratory Disease (BRD)", "score": 0.87, "source": "image"})
        # create a dummy gradcam (just re-save the uploaded image into gradcam folder)
        try:
            uid = str(uuid.uuid4())[:8] + ".jpg"
            gradcam_path = os.path.join(GRADCAM_DIR, uid)
            Image.open(io.BytesIO(content)).convert("RGB").resize((224,224)).save(gradcam_path)
            gradcam_url = f"/media/gradcams/{uid}"
        except Exception:
            gradcam_url = None

    # If symptom_text present: dummy text model
    if symptom_text and len(symptom_text.strip())>0:
        # dummy text prediction
        predictions.append({"disease": "Mastitis", "score": 0.45, "source": "text"})

    # Ensemble logic (simple)
    # Give image predictions weight 0.6, text 0.4 when both exist
    # Here we just sort by score for demo
    predictions = sorted(predictions, key=lambda x: x["score"], reverse=True)
    top = predictions[0] if predictions else {"disease": "Unknown", "score": 0.0}

    # confidence: top score
    confidence = float(top.get("score", 0.0))

    # severity heuristic
    severity = "low"
    if confidence > 0.8:
        severity = "high"
    elif confidence > 0.5:
        severity = "medium"

    response = {
        "predictions": predictions,
        "top": top,
        "confidence": confidence,
        "severity": severity,
        "gradcam_url": gradcam_url,
        "model_version": MODEL_VERSION,
        "case_id": case_id
    }
    return response
