# SleepWise Backend

Flask backend for the SleepWise health prediction application.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

## API Endpoints

### POST /predict
Predicts sleep quality and provides health suggestions based on user metrics.

**Request Body:**
```json
{
    "heartRate": 70,
    "steps": 8000,
    "activityLevel": "Moderate"
}
```

**Response:**
```json
{
    "sleepQuality": "Good",
    "healthScore": 75.5,
    "suggestions": [
        "Strong metrics with room for fine-tuning",
        "Heart Rate: 70 BPM (Good)",
        "Steps: 8,000 (Good)",
        "Consider timing of exercise relative to sleep",
        "Monitor caffeine intake timing"
    ]
}
```

## Deployment

This backend is configured for deployment on Render.com using the following files:
- `requirements.txt`: Python dependencies
- `Procfile`: Command to run the application
- `render.yaml`: Render configuration
