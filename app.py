from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from datetime import datetime
import json
import random
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure CORS for production
ALLOWED_ORIGINS = [
    'http://localhost:4321',  # Local development
    'http://127.0.0.1:4321',  # Local development alternative
    'https://sleep-wise.netlify.app',  # Production frontend
    'https://sleepwise.netlify.app',   # Alternative production frontend
    'https://*.netlify.app'  # Any Netlify preview deployments
]

CORS(app, resources={
    r"/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": False,
        "max_age": 3600
    }
})

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin and (origin in ALLOWED_ORIGINS or any(origin.endswith(domain.replace('*', '')) for domain in ALLOWED_ORIGINS if '*' in domain)):
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Max-Age', '3600')
    return response

def activity_to_acceleration(level):
    mapping = {
        "Low": 0.3 + (random.random() * 0.4),      # 0.3-0.7
        "Moderate": 1.0 + (random.random() * 0.8),  # 1.0-1.8
        "High": 1.8 + (random.random() * 1.2)       # 1.8-3.0
    }
    return mapping.get(level, 1.0)

def calculate_health_score(heart_rate, steps, activity_level):
    # Define expected ranges based on activity level
    activity_ranges = {
        "Low": {
            "hr_optimal_range": (60, 75),
            "steps_target": 8000,
            "steps_min": 4000,
        },
        "Moderate": {
            "hr_optimal_range": (55, 70),
            "steps_target": 12000,
            "steps_min": 7000,
        },
        "High": {
            "hr_optimal_range": (45, 65),
            "steps_target": 15000,
            "steps_min": 10000,
        }
    }

    current_range = activity_ranges[activity_level]
    hr_min, hr_max = current_range["hr_optimal_range"]

    # Heart rate scoring - more punitive for extreme values
    if hr_min <= heart_rate <= hr_max:
        hr_score = 1.0
    elif heart_rate < hr_min:
        # Penalize very low heart rates more severely
        hr_score = max(0.3, 0.7 + (heart_rate - (hr_min - 10)) / (hr_min - (hr_min - 10)) * 0.3)
    else:
        # Penalize high heart rates more severely
        hr_score = max(0.2, 1.0 - ((heart_rate - hr_max) / 30))

    # Steps scoring with minimum threshold
    steps_min = current_range["steps_min"]
    steps_target = current_range["steps_target"]

    if steps < steps_min:
        # Severe penalty for very low steps
        steps_score = max(0.2, steps / steps_min * 0.5)
    else:
        steps_score = min(1.0, (steps - steps_min) / (steps_target - steps_min))

    # Activity level consistency score - more punitive for inconsistencies
    consistency_score = 1.0

    # Severe inconsistency penalties
    if activity_level == "High":
        if steps < 8000:
            consistency_score *= 0.4  # Severe penalty for high activity but very low steps
        elif steps < 10000:
            consistency_score *= 0.6
        if heart_rate > 80:
            consistency_score *= 0.5  # High resting HR inconsistent with high activity

    elif activity_level == "Moderate":
        if steps < 5000:
            consistency_score *= 0.5
        if heart_rate > 90:
            consistency_score *= 0.6

    elif activity_level == "Low":
        if steps > 15000:
            consistency_score *= 0.6  # Inconsistent with claimed low activity
        if heart_rate < 50:
            consistency_score *= 0.7  # Too low HR for low activity

    # Extreme cases penalties
    if heart_rate > 100:
        consistency_score *= 0.4  # Severe penalty for very high resting HR
    if steps < 2000:
        consistency_score *= 0.3  # Severe penalty for extremely sedentary

    # Calculate base score with adjusted weights
    base_score = (hr_score * 0.35 + steps_score * 0.35 + consistency_score * 0.3) * 100

    # Additional penalties for extreme poor scenarios
    if steps < 2000 and heart_rate > 90:
        base_score *= 0.6  # Severe penalty for very unhealthy combination

    # Cap the minimum score at 20 to allow for very poor scenarios
    base_score = max(20, base_score)

    return base_score, hr_score, steps_score, consistency_score

def predict_and_suggest(activity_level, heart_rate, steps):
    try:
        acceleration = activity_to_acceleration(activity_level)

        # Calculate comprehensive health score
        base_score, hr_score, steps_score, consistency_score = calculate_health_score(heart_rate, steps, activity_level)

        suggestions = []
        if base_score >= 85:
            sleep_quality = "Excellent"
            suggestions = [
                "⭐ Excellent metrics with great consistency!\n",
                "• Heart Rate: {} BPM (Optimal)\n".format(heart_rate),
                "• Steps: {:,} (Excellent)\n".format(steps),
                "• Maintain your current balanced routine\n",
                "• Consider heart rate variability tracking"
            ]
        elif 70 <= base_score < 85:
            sleep_quality = "Good"
            suggestions = [
                "🎯 Strong metrics with room for fine-tuning\n",
                "• Heart Rate: {} BPM (Good)\n".format(heart_rate),
                "• Steps: {:,} (Good)\n".format(steps),
                "• Consider timing of exercise relative to sleep\n",
                "• Monitor caffeine intake timing"
            ]
        elif 55 <= base_score < 70:
            sleep_quality = "Fair"
            suggestions = [
                "💪 Good foundation with opportunities for improvement\n",
                "• Heart Rate: {} BPM (Needs attention)\n".format(heart_rate),
                "• Steps: {:,} (Could be improved)\n".format(steps),
                "• Implement regular relaxation practices\n",
                "• Review exercise timing and intensity"
            ]
        else:
            sleep_quality = "Poor"
            suggestions = [
                "⚠️ Your metrics indicate room for improvement\n",
                "• Heart Rate: {} BPM (Needs improvement)\n".format(heart_rate),
                "• Steps: {:,} (Below recommended minimum)\n".format(steps),
                "• Start with simple walking routine\n",
                "• Focus on stress reduction techniques"
            ]

        return sleep_quality, base_score, "\n".join(suggestions)

    except Exception as e:
        return "Error", 0, f"Error: {str(e)}"

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        activity_level = data.get('activityLevel', 'Moderate')
        heart_rate = int(data.get('heartRate', 70))
        steps = int(data.get('steps', 0))
        
        sleep_quality, health_score, suggestions = predict_and_suggest(activity_level, heart_rate, steps)
        
        return jsonify({
            'sleepQuality': sleep_quality,
            'healthScore': f"{health_score:.1f}",
            'suggestions': suggestions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=True)
