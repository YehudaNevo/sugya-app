
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from openai import OpenAI
import os
import re
import time
from collections import defaultdict
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security configuration
ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Local development
    "https://sugya-app-frontend.onrender.com",  # Production frontend
    "http://localhost:4173",  # Vite preview
]

# Configure CORS properly
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Security constants
MAX_MESSAGE_LENGTH = 1000
MAX_MESSAGES_PER_REQUEST = 20
SUSPICIOUS_PATTERNS = [
    r"ignore\s+previous\s+instructions?",
    r"system\s*prompt",
    r"you\s+are\s+now",
    r"forget\s+everything",
    r"new\s+instructions?",
    r"override\s+your",
    r"jailbreak",
    r"developer\s+mode",
]

class ChatRequest(BaseModel):
    messages: list
    
    @validator('messages')
    def validate_messages(cls, messages):
        if not messages or len(messages) > MAX_MESSAGES_PER_REQUEST:
            raise ValueError(f"Messages must be between 1 and {MAX_MESSAGES_PER_REQUEST}")
        
        for msg in messages:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                raise ValueError("Invalid message format")
            
            if len(msg['content']) > MAX_MESSAGE_LENGTH:
                raise ValueError(f"Message too long (max {MAX_MESSAGE_LENGTH} characters)")
            
            # Check for prompt injection attempts
            content_lower = msg['content'].lower()
            for pattern in SUSPICIOUS_PATTERNS:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    raise ValueError("Message contains suspicious content")
        
        return messages

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Simple in-memory store for session tracking (use Redis in production)
session_store = defaultdict(lambda: {"count": 0, "last_reset": time.time()})

def get_client_ip(request: Request) -> str:
    """Get client IP, considering proxy headers"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host

def check_session_limits(client_ip: str) -> bool:
    """Check if client has exceeded session limits"""
    current_time = time.time()
    session = session_store[client_ip]
    
    # Reset counter every hour
    if current_time - session["last_reset"] > 3600:
        session["count"] = 0
        session["last_reset"] = current_time
    
    # Limit: 100 requests per hour per IP
    if session["count"] >= 100:
        return False
    
    session["count"] += 1
    return True

def filter_system_messages(messages: list) -> list:
    """Filter and validate system messages to prevent prompt injection"""
    filtered_messages = []
    allowed_system_content = {
        "חברותא דיגיטלית", "ייאוש שלא מדעת", "אביי", "רבא", "chavruta", "abaye", "rava"
    }
    
    for msg in messages:
        if msg.get("role") == "system":
            # Only allow system messages that contain expected keywords
            content_lower = msg["content"].lower()
            if any(keyword.lower() in content_lower for keyword in allowed_system_content):
                filtered_messages.append(msg)
            # Skip suspicious system messages
        else:
            filtered_messages.append(msg)
    
    return filtered_messages

@app.get("/")
async def root():
    return {"message": "Sugya App Backend API"}

@app.post("/api/chat")
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute per IP
async def chat(request: Request, chat_request: ChatRequest):
    if not client.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not set")

    # Get client IP and check session limits
    client_ip = get_client_ip(request)
    if not check_session_limits(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    try:
        # Filter and validate messages
        filtered_messages = filter_system_messages(chat_request.messages)
        
        if not filtered_messages:
            raise HTTPException(status_code=400, detail="No valid messages provided")

        # Additional safety: limit total tokens
        total_chars = sum(len(msg["content"]) for msg in filtered_messages)
        if total_chars > 5000:
            raise HTTPException(status_code=400, detail="Request too large")

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=filtered_messages,
            max_tokens=1000,  # Limit response length
            temperature=0.7,
            timeout=30  # 30 second timeout
        )
        
        return completion.choices[0].message
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        raise HTTPException(status_code=500, detail="Failed to process request")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

