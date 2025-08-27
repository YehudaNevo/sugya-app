
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configure CORS for development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    messages: list

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
async def root():
    return {"message": "Sugya App Backend API"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not client.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not set")

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=request.messages
        )
        return completion.choices[0].message
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenAI")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

