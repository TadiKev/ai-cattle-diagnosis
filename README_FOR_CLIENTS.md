# AI Cattle Diagnosis — Client Quickstart (Windows first)

This repo: https://github.com/TadiKev/ai-cattle-diagnosis

**Summary** — three components:
- `backend-django/` — Django API (port 8000)
- `ml-inference/` — FastAPI model server (port 8001) — **needs model files**
- `frontend/` — React frontend (Vite)

**We do NOT commit heavy files (models/dataset).** Use the fetch script to download required model assets.

---

## 1) Get model files (one-time)
Publish a GitHub Release with assets `best_model_state_dict.pth` and `class_map.json`. After that:

PowerShell (Windows):
```powershell
cd C:\path\to\ai-cattle-diagnosis
.\scripts\fetch_assets.ps1 -baseUrl "https://github.com/TadiKev/ai-cattle-diagnosis/releases/download/v1.0.0"
