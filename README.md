# Vision Inspection AI Trainer (DataMatrix ROI-Based Detection System)

Production-style ROI-based DataMatrix inspection app with FastAPI + React.

## Features

- Teach mode: upload an image and define a DataMatrix ROI
- Template persistence with grayscale + edge representations
- Detection mode: template matching + DataMatrix decode + confidence + timing
- Camera mode: start/stop live inspection loop (RTSP or local camera index)
- Industrial-style frontend with ROI drawing and detection overlay

## Tech Stack

- Backend: FastAPI, OpenCV, NumPy, pylibdmtx
- Frontend: React + Vite
- Vision strategy: grayscale + Canny + `cv2.matchTemplate` + ROI decode

## Project Structure

```text
project/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── routes/
│   │   ├── teach.py
│   │   ├── detect.py
│   │   └── camera.py
│   ├── services/
│   │   ├── template_manager.py
│   │   ├── detection.py
│   │   ├── decoding.py
│   │   └── optimization.py
│   ├── utils/
│   │   ├── image_processing.py
│   │   └── timer.py
│   ├── templates/
│   └── uploads/
└── frontend/
```

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

`GET http://127.0.0.1:8000/health`

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open:

`http://127.0.0.1:5173`

## API

### 1) Teach

`POST /teach`

Form fields:

- `image`: image file
- `x`, `y`, `width`, `height`: ROI values in 640x480 canvas coordinates

Response:

- `template_id`
- `roi`
- `message`

### 2) Detect

`POST /detect?template_id=<id>`

Form fields:

- `image`: image file

Response:

- `decoded_data`
- `bounding_box`
- `confidence_score`
- `processing_time_ms`
- `status` (`GOOD` / `BAD`)

### 3) Camera

- `GET /camera/start?template_id=<id>`
- `GET /camera/stop`
- `GET /camera/status`

Set `CAMERA_URL` for RTSP or use local webcam index (`0`):

```bash
set CAMERA_URL=rtsp://user:pass@camera-ip/stream
```

## Performance Notes

- Fixed-size preprocessing at 640x480 for stable runtime
- Grayscale + Canny for light, deterministic matching
- ROI-only decode path after template match
- Frame skipping in camera mode for higher throughput
- Typical processing target is `< 50 ms` depending on hardware and image quality

## Usage Flow

1. Upload a teach image
2. Draw ROI over the DataMatrix
3. Click **Teach ROI**
4. Upload a detect image
5. Click **Detect DataMatrix**
6. Inspect status, decoded data, confidence, and timing
