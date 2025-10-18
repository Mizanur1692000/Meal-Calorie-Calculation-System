import os
import uuid
import json
import re
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Initialize FastAPI app
app = FastAPI(title="AI Meal Calorie Calculator")

# In-memory storage for analyzed meals
meal_analyses = {}

# --- Helper function: safely extract valid JSON from Gemini response ---
def extract_json(text: str):
    """Extract and parse JSON safely from Gemini output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        # Fallback
        return {
            "foods": [],
            "total_calories": "N/A",
            "protein_g": "N/A",
            "carbs_g": "N/A",
            "fat_g": "N/A",
            "summary": "Unable to parse response properly."
        }

# --- Root route ---
@app.get("/")
def home():
    return {"message": "Welcome to the AI Meal Calorie Calculator API!"}


# --- Upload Meal & Analyze ---
@app.post("/upload-meal")
async def upload_meal(
    image: UploadFile = File(...),
    meal_type: Optional[str] = Form(None)
):
    """
    Upload meal image -> Gemini analyzes -> returns analysis_id
    """
    try:
        image_bytes = await image.read()
        analysis_id = str(uuid.uuid4())

        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = """
        You are a certified nutritionist AI. Analyze this meal image and return ONLY a JSON object:
        {
          "foods": ["food1", "food2", ...],
          "total_calories": <number>,
          "protein_g": <number>,
          "carbs_g": <number>,
          "fat_g": <number>,
          "summary": "short healthy suggestion"
        }
        """

        # Gemini call
        response = model.generate_content(
            [prompt, {"mime_type": image.content_type, "data": image_bytes}]
        )

        raw_text = response.text.strip()
        parsed = extract_json(raw_text)

        # Fill missing keys to ensure UI consistency
        parsed.setdefault("foods", [])
        parsed.setdefault("total_calories", "N/A")
        parsed.setdefault("protein_g", "N/A")
        parsed.setdefault("carbs_g", "N/A")
        parsed.setdefault("fat_g", "N/A")
        parsed.setdefault("summary", "N/A")

        # Save analysis in memory
        meal_analyses[analysis_id] = {
            "meal_type": meal_type or "unknown",
            "timestamp": datetime.now().isoformat(),
            "foods": parsed["foods"],
            "total_calories": parsed["total_calories"],
            "protein_g": parsed["protein_g"],
            "carbs_g": parsed["carbs_g"],
            "fat_g": parsed["fat_g"],
            "summary": parsed["summary"]
        }

        return {
            "message": f"Meal analyzed successfully ({meal_type or 'unspecified'}).",
            "analysis_id": analysis_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini Error: {str(e)}")


# --- Unified Full Analysis ---
@app.get("/get-analysis/{analysis_id}")
def get_analysis(analysis_id: str):
    data = meal_analyses.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis ID not found.")
    return data


# --- Individual Endpoints for UI Integration ---

@app.get("/get-calories/{analysis_id}")
def get_calories(analysis_id: str):
    data = meal_analyses.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis ID not found.")
    return {
        "analysis_id": analysis_id,
        "total_calories": data["total_calories"]
    }

@app.get("/get-proteins/{analysis_id}")
def get_proteins(analysis_id: str):
    data = meal_analyses.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis ID not found.")
    return {
        "analysis_id": analysis_id,
        "protein_g": data["protein_g"]
    }

@app.get("/get-carbs/{analysis_id}")
def get_carbs(analysis_id: str):
    data = meal_analyses.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis ID not found.")
    return {
        "analysis_id": analysis_id,
        "carbs_g": data["carbs_g"]
    }

@app.get("/get-fats/{analysis_id}")
def get_fats(analysis_id: str):
    data = meal_analyses.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis ID not found.")
    return {
        "analysis_id": analysis_id,
        "fat_g": data["fat_g"]
    }

@app.get("/get-suggestions/{analysis_id}")
def get_suggestions(analysis_id: str):
    data = meal_analyses.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis ID not found.")
    return {
        "analysis_id": analysis_id,
        "suggestions": data["summary"]
    }
