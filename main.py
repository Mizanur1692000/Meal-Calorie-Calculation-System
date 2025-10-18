# import os
# import uuid
# import json
# import re
# from datetime import datetime
# from typing import Optional
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException
# from fastapi.responses import JSONResponse
# from dotenv import load_dotenv
# import google.generativeai as genai

# # Load environment variables
# load_dotenv()
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# if not GEMINI_API_KEY:
#     raise ValueError("❌ GEMINI_API_KEY not found in .env file")

# # Configure Gemini
# genai.configure(api_key=GEMINI_API_KEY)

# # Initialize FastAPI app
# app = FastAPI(title="AI Meal Calorie Calculator")

# # In-memory storage for analyzed meals
# meal_analyses = {}

# # --- Helper function: safely extract valid JSON from Gemini response ---
# def extract_json(text: str):
#     """Extract and parse JSON safely from Gemini output."""
#     try:
#         return json.loads(text)
#     except json.JSONDecodeError:
#         match = re.search(r'\{.*\}', text, re.DOTALL)
#         if match:
#             try:
#                 return json.loads(match.group(0))
#             except json.JSONDecodeError:
#                 pass
#         # Fallback
#         return {
#             "foods": [],
#             "total_calories": "N/A",
#             "protein_g": "N/A",
#             "carbs_g": "N/A",
#             "fat_g": "N/A",
#             "summary": "Unable to parse response properly."
#         }

# # --- Root route ---
# @app.get("/")
# def home():
#     return {"message": "Welcome to the AI Meal Calorie Calculator API!"}


# # --- Upload Meal & Analyze ---
# @app.post("/upload-meal")
# async def upload_meal(
#     image: UploadFile = File(...),
#     meal_type: Optional[str] = Form(None)
# ):
#     """
#     Upload meal image -> Gemini analyzes -> returns analysis_id
#     """
#     try:
#         image_bytes = await image.read()
#         analysis_id = str(uuid.uuid4())

#         model = genai.GenerativeModel("gemini-2.5-flash")

#         prompt = """
#         You are a certified nutritionist AI. Analyze this meal image and return ONLY a JSON object:
#         {
#           "foods": ["food1", "food2", ...],
#           "total_calories": <number>,
#           "protein_g": <number>,
#           "carbs_g": <number>,
#           "fat_g": <number>,
#           "summary": "short healthy suggestion"
#         }
#         """

#         # Gemini call
#         response = model.generate_content(
#             [prompt, {"mime_type": image.content_type, "data": image_bytes}]
#         )

#         raw_text = response.text.strip()
#         parsed = extract_json(raw_text)

#         # Fill missing keys to ensure UI consistency
#         parsed.setdefault("foods", [])
#         parsed.setdefault("total_calories", "N/A")
#         parsed.setdefault("protein_g", "N/A")
#         parsed.setdefault("carbs_g", "N/A")
#         parsed.setdefault("fat_g", "N/A")
#         parsed.setdefault("summary", "N/A")

#         # Save analysis in memory
#         meal_analyses[analysis_id] = {
#             "meal_type": meal_type or "unknown",
#             "timestamp": datetime.now().isoformat(),
#             "foods": parsed["foods"],
#             "total_calories": parsed["total_calories"],
#             "protein_g": parsed["protein_g"],
#             "carbs_g": parsed["carbs_g"],
#             "fat_g": parsed["fat_g"],
#             "summary": parsed["summary"]
#         }

#         return {
#             "message": f"Meal analyzed successfully ({meal_type or 'unspecified'}).",
#             "analysis_id": analysis_id
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Gemini Error: {str(e)}")


# # --- Unified Full Analysis ---
# @app.get("/get-analysis/{analysis_id}")
# def get_analysis(analysis_id: str):
#     data = meal_analyses.get(analysis_id)
#     if not data:
#         raise HTTPException(status_code=404, detail="Analysis ID not found.")
#     return data


# # --- Individual Endpoints for UI Integration ---

# @app.get("/get-calories/{analysis_id}")
# def get_calories(analysis_id: str):
#     data = meal_analyses.get(analysis_id)
#     if not data:
#         raise HTTPException(status_code=404, detail="Analysis ID not found.")
#     return {
#         "analysis_id": analysis_id,
#         "total_calories": data["total_calories"]
#     }

# @app.get("/get-proteins/{analysis_id}")
# def get_proteins(analysis_id: str):
#     data = meal_analyses.get(analysis_id)
#     if not data:
#         raise HTTPException(status_code=404, detail="Analysis ID not found.")
#     return {
#         "analysis_id": analysis_id,
#         "protein_g": data["protein_g"]
#     }

# @app.get("/get-carbs/{analysis_id}")
# def get_carbs(analysis_id: str):
#     data = meal_analyses.get(analysis_id)
#     if not data:
#         raise HTTPException(status_code=404, detail="Analysis ID not found.")
#     return {
#         "analysis_id": analysis_id,
#         "carbs_g": data["carbs_g"]
#     }

# @app.get("/get-fats/{analysis_id}")
# def get_fats(analysis_id: str):
#     data = meal_analyses.get(analysis_id)
#     if not data:
#         raise HTTPException(status_code=404, detail="Analysis ID not found.")
#     return {
#         "analysis_id": analysis_id,
#         "fat_g": data["fat_g"]
#     }

# @app.get("/get-suggestions/{analysis_id}")
# def get_suggestions(analysis_id: str):
#     data = meal_analyses.get(analysis_id)
#     if not data:
#         raise HTTPException(status_code=404, detail="Analysis ID not found.")
#     return {
#         "analysis_id": analysis_id,
#         "suggestions": data["summary"]
#     }




from fastapi import FastAPI, UploadFile, File, Form
from datetime import datetime
import uuid
import json
import re
import google.generativeai as genai
import tempfile
import os
from PIL import Image
import io
from dotenv import load_dotenv

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file")

# Configure Gemini with the API key
genai.configure(api_key=api_key)

# -------------------------------
# Initialize FastAPI app
# -------------------------------
app = FastAPI(title= "AI Meal Calorie Calculator & Fitness Coach")

# In-memory data store
users = {}

# -------------------------------
# Utility: Safe JSON Parser
# -------------------------------
def safe_json_parse(text):
    try:
        clean = re.search(r"\{.*\}", text, re.DOTALL)
        if clean:
            return json.loads(clean.group())
    except Exception:
        pass
    return None


# -------------------------------
# 1️⃣ Create / Update User Profile
# -------------------------------
@app.post("/set-profile")
async def set_profile(
    name: str = Form(...),
    age: int = Form(...),
    sex: str = Form(...),
    weight_kg: float = Form(...),
    height_cm: float = Form(...),
    activity_level: str = Form(...),
    goal: str = Form(...),
):
    user_id = str(uuid.uuid4())
    users[user_id] = {
        "profile": {
            "name": name,
            "age": age,
            "sex": sex,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "activity_level": activity_level,
            "goal": goal,
        },
        "meal_history": [],
        "recommendations": {},
        "workouts": [],
        "progress": [],
        "notifications": [],
    }
    return {"message": "User profile created successfully", "user_id": user_id}


# --------------------------------
# 2️⃣ Upload Meal Image & Analyze
# --------------------------------
@app.post("/upload-meal")
async def upload_meal(user_id: str = Form(...), file: UploadFile = File(...)):
    if user_id not in users:
        return {"error": "User not found. Please create a profile first."}

    # Convert uploaded bytes to PIL image
    image_bytes = await file.read()
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return {"error": "Invalid image file."}

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        analysis_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        prompt = f"""
        You are a certified nutritionist AI.
        User Profile: {users[user_id]['profile']}
        Analyze this meal image and return valid JSON only (no explanation):
        {{
          "analysis_id": "{analysis_id}",
          "datetime": "{timestamp}",
          "total_calories": 0,
          "protein": 0,
          "carbs": 0,
          "fats": 0,
          "suggestions": "short healthy meal advice"
        }}
        """

        # Pass PIL.Image directly to Gemini
        response = model.generate_content([prompt, img])
        parsed = safe_json_parse(response.text)

        if not parsed:
            return {"error": "Invalid AI response", "raw": response.text}

        users[user_id]["meal_history"].append(parsed)
        return {"message": "Meal analyzed successfully", "data": parsed}

    except Exception as e:
        return {"error": f"Meal analysis failed: {str(e)}"}


# --------------------------------
# 3️⃣ Goal-Based Nutrition Advice
# --------------------------------
@app.get("/nutrition-recommendations/{user_id}")
async def nutrition_recommendations(user_id: str):
    if user_id not in users:
        return {"error": "User not found."}

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    Based on this user profile:
    {users[user_id]['profile']}
    Provide JSON only with daily nutritional goals and example meals:
    {{
      "recommended_calories": 0,
      "recommended_protein": 0,
      "recommended_carbs": 0,
      "recommended_fats": 0,
      "meal_suggestions": ["Breakfast: ...", "Lunch: ...", "Dinner: ..."]
    }}
    """

    try:
        response = model.generate_content(prompt)
        parsed = safe_json_parse(response.text)
        if not parsed:
            return {"error": "Invalid AI response", "raw": response.text}
        users[user_id]["recommendations"] = parsed
        return {"message": "Nutrition recommendation generated", "data": parsed}
    except Exception as e:
        return {"error": f"Failed to generate recommendations: {str(e)}"}


# --------------------------------
# 4️⃣ AI-Enhanced Workouts
# --------------------------------
@app.get("/ai-workout/{user_id}")
async def ai_workout(user_id: str):
    if user_id not in users:
        return {"error": "User not found."}

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    You are an AI fitness coach.
    User profile: {users[user_id]['profile']}
    Suggest a 1-day personalized workout plan in JSON only:
    {{
      "goal": "{users[user_id]['profile']['goal']}",
      "exercises": [
        {{"name": "Push-ups", "sets": 3, "reps": 12}},
        {{"name": "Squats", "sets": 3, "reps": 15}}
      ],
      "tips": "Stay hydrated and maintain proper form."
    }}
    """

    try:
        response = model.generate_content(prompt)
        parsed = safe_json_parse(response.text)
        if not parsed:
            return {"error": "Invalid AI response", "raw": response.text}
        users[user_id]["workouts"].append(parsed)
        return {"message": "Workout plan generated", "data": parsed}
    except Exception as e:
        return {"error": f"Workout generation failed: {str(e)}"}


# --------------------------------
# 5️⃣ Progress Insights
# --------------------------------
@app.get("/progress-insights/{user_id}")
async def progress_insights(user_id: str):
    if user_id not in users:
        return {"error": "User not found."}

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    Analyze user's meal and workout history:
    Meals: {users[user_id]['meal_history']}
    Workouts: {users[user_id]['workouts']}
    Return JSON only:
    {{
      "progress_summary": "short summary",
      "nutrition_pattern": "summary of macro balance",
      "performance_trend": "improving/declining",
      "suggested_next_steps": "AI feedback for next week"
    }}
    """

    try:
        response = model.generate_content(prompt)
        parsed = safe_json_parse(response.text)
        if not parsed:
            return {"error": "Invalid AI response", "raw": response.text}
        users[user_id]["progress"].append(parsed)
        return {"message": "Progress insights generated", "data": parsed}
    except Exception as e:
        return {"error": f"Failed to analyze progress: {str(e)}"}


# --------------------------------
# 6️⃣ Personalized Adjustments
# --------------------------------
@app.get("/personalized-adjustments/{user_id}")
async def personalized_adjustments(user_id: str):
    if user_id not in users:
        return {"error": "User not found."}

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    Based on user profile and history:
    Profile: {users[user_id]['profile']}
    Meals: {users[user_id]['meal_history']}
    Workouts: {users[user_id]['workouts']}
    Suggest adjustments in JSON only:
    {{
      "nutrition_adjustment": "short summary",
      "workout_adjustment": "short summary",
      "motivation_tip": "short motivational quote"
    }}
    """

    try:
        response = model.generate_content(prompt)
        parsed = safe_json_parse(response.text)
        if not parsed:
            return {"error": "Invalid AI response", "raw": response.text}
        return {"message": "Personalized adjustments ready", "data": parsed}
    except Exception as e:
        return {"error": f"Failed to get adjustments: {str(e)}"}


# --------------------------------
# 7️⃣ Motivation & Notifications
# --------------------------------
@app.get("/motivations/{user_id}")
async def motivations(user_id: str):
    if user_id not in users:
        return {"error": "User not found."}

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    You are a motivational coach.
    Based on user's goal: {users[user_id]['profile']['goal']}
    Return JSON only:
    {{
      "daily_quote": "motivational message",
      "reminder": "hydration/workout reminder",
      "encouragement": "progress motivation"
    }}
    """

    try:
        response = model.generate_content(prompt)
        parsed = safe_json_parse(response.text)
        if not parsed:
            return {"error": "Invalid AI response", "raw": response.text}
        users[user_id]["notifications"].append(parsed)
        return {"message": "Motivational data generated", "data": parsed}
    except Exception as e:
        return {"error": f"Failed to get motivation: {str(e)}"}

