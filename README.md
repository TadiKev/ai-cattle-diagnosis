# AI Cattle Disease Diagnosis System

This application provides an intelligent cattle disease diagnosis tool designed for farms, veterinary professionals, and livestock managers.  
It combines computer vision, symptom analysis, and rule-based recommendations to assist with early detection and management of common cattle diseases.

---

## Key Features

- **Image-based diagnosis** using a trained deep-learning model  
- **Symptom-assisted analysis** to improve prediction reliability  
- **Grad-CAM heatmaps** showing the model’s focus areas  
- **Automatic treatment suggestions** based on disease type  
- **Weight-based dosage calculation** (mg/kg × cattle weight)  
- **Cattle profiles and records management**  
- **Diagnosis history and per-animal tracking**  
- **Modern React interface + Django REST API**  
- **Separate inference service for model processing**  
- **Full Docker setup for easy deployment**

---

## Project Structure

```

ai-cattle-diagnosis/
│
├── backend-django/        # Django API (authentication, records, history)
├── frontend/              # React frontend (UI)
├── ml-inference/          # Inference microservice (model + Grad-CAM)
├── metadata/              # treatment_map.json
├── docker-compose.yml
└── README.md

````

---

# Running the System

You can run it using **Docker** or **manual setup**.

---

# Option 1: Run with Docker (Recommended)

### 1. Clone the repository

```bash
git clone https://github.com/TadiKev/ai-cattle-diagnosis.git
cd ai-cattle-diagnosis
````

### 2. Create environment files

```bash
cp backend-django/.env.example backend-django/.env
cp ml-inference/.env.example ml-inference/.env
```

Update keys, DB credentials, and model paths as needed.

### 3. Start the stack

```bash
docker-compose up --build
```

### 4. Access the system

| Service              | URL                                                        |
| -------------------- | ---------------------------------------------------------- |
| Frontend             | [http://localhost:3000](http://localhost:3000)             |
| Backend API          | [http://localhost:8000/api/](http://localhost:8000/api/)   |
| Django Admin         | [http://localhost:8000/admin](http://localhost:8000/admin) |
| ML Inference Service | [http://localhost:7000/infer](http://localhost:7000/infer) |

---

# Option 2: Manual Setup

### Backend (Django)

```bash
cd backend-django
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Backend available at: **[http://localhost:8000](http://localhost:8000)**

---

### ML Inference Service

```bash
cd ml-inference
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Inference endpoint: **[http://localhost:7000/infer](http://localhost:7000/infer)**

---

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

UI available at: **[http://localhost:3000](http://localhost:3000)**

---

# Environment Variables

### Backend `.env`

```
SECRET_KEY=your_secret_key
DEBUG=True
DB_NAME=cattle_ai
DB_USER=postgres
DB_PASSWORD=pass
DB_HOST=localhost
DB_PORT=5432
ML_API_URL=http://localhost:7000/infer
```

### ML Inference `.env`

```
MODEL_PATH=models/cattle_model.pt
HOST=0.0.0.0
PORT=7000
```

---

# AI Model and Processing

* Uses a convolutional neural network for image classification
* Supports multiple images per diagnosis
* Generates Grad-CAM heatmaps for transparency
* Includes symptom-based adjustments to predictions

---

# Treatment Recommendation System

Treatment rules are stored in:

```
backend-django/metadata/treatment_map.json
```

A Django script automatically attaches treatment text to each diagnosis and, when weight is available, calculates a total dosage based on mg/kg.
