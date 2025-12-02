# AI Cattle Disease Diagnosis — Repo Skeleton

This repository contains the skeleton for the AI Cattle Disease Diagnosis project.

Folders:
- /backend-django: Django + DRF app
- /ml-inference: FastAPI inference microservice
- /frontend: React app
- /models: trained artifacts (gitignored)
- /data: datasets & notebooks (gitignored)
- /docs: documentation (threat model, dataset licenses, design notes)

## Phase 0 deliverable
This repo contains the skeleton, Dockerfiles and `docker-compose.yml` for local development.

## Quick start (development)
1. Copy `.env.example` to `.env` and fill values.
2. Build & run (local):

3. Services (local dev):
- Django backend: http://localhost:8000
- FastAPI inference: http://localhost:8001
- Frontend (Vite/React): http://localhost:3000

## Next steps
- Scaffold Django project under `/backend-django` (manage.py, settings, apps).
- Create FastAPI `inference.py` inside `/ml-inference`.
- Initialize frontend app (Vite) inside `/frontend`.
