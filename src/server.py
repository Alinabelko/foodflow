import os
import shutil
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from data_manager import DataManager
from agents.router_agent import RouterAgent
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, set to specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dm = DataManager()
agent = RouterAgent(dm)

class ChatRequest(BaseModel):
    message: str

class SettingsRequest(BaseModel):
    language: str

@app.get("/api/data/{filename}")
async def get_data(filename: str):
    if filename not in dm.SCHEMAS:
        raise HTTPException(status_code=404, detail="File not found")
    return dm.read_table(filename)

@app.post("/api/meal_plans/approve")
async def approve_meal_plan(date: str = Form(...)):
    # Update all entries for this date to 'confirmed'
    # Simplified logic: Read, Update, Save.
    # Ideally DataManager should handle this
    dm.update_entry('meal_plans.csv', 'date', date, {'status': 'confirmed'})
    return {"status": "success"}

@app.post("/api/data/{filename}")
async def save_data(filename: str, data: List[dict]):
    if filename not in dm.SCHEMAS:
        raise HTTPException(status_code=404, detail="File not found")
    dm.save_table(filename, data)
    return {"status": "success"}

@app.get("/api/settings")
async def get_settings():
    return dm.get_settings()

@app.post("/api/settings")
async def save_settings(settings: SettingsRequest):
    current = dm.get_settings()
    current["language"] = settings.language
    dm.save_settings(current)
    return {"status": "success"}

@app.post("/api/translate_database")
async def translate_database(settings: SettingsRequest):
    # Depending on load, this might timeout. In prod, background task.
    # For now, simplistic sync wait.
    agent.translate_database(settings.language)
    agent.translate_database(settings.language)
    return {"status": "success"}

@app.post("/api/clear_chat")
async def clear_chat():
    agent.clear_history()
    return {"status": "success"}

@app.post("/api/chat")
async def chat(
    message: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    image_path = None
    if image:
        # Save temp image
        image_path = f"temp_{image.filename}"
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
            
    try:
        result = agent.process_message(message, image_path)
        if isinstance(result, dict):
            return result
        return {"response": str(result), "logs": []}
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
