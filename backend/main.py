
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from openai import OpenAI
import os
import re
import time
import json
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

# Security constants - more flexible
MAX_MESSAGE_LENGTH = 5000
MAX_MESSAGES_PER_REQUEST = 50
SUSPICIOUS_PATTERNS = [
    r"ignore\s+all\s+previous\s+instructions",
    r"you\s+are\s+now\s+chatgpt",
    r"forget\s+everything\s+above",
    r"new\s+system\s+instructions",
    r"override\s+system\s+prompt",
    r"jailbreak\s+mode",
]

class ChatRequest(BaseModel):
    messages: list
    
    @field_validator('messages')
    @classmethod
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
    
    # Limit: 1000 requests per hour per IP
    if session["count"] >= 1000:
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

async def generate_stream(filtered_messages: list):
    """Generate streaming response from OpenAI"""
    try:
        
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=filtered_messages,
            max_tokens=1000,
            temperature=0.7,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                print(f"Streaming chunk: {content}")  # Debug log
                yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
        
        # Send completion signal
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
        
    except Exception as e:
        print(f"Error in streaming: {e}")
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

@app.post("/api/chat")
@limiter.limit("100/minute")  # Rate limit: 100 requests per minute per IP
async def chat(request: Request, chat_request: ChatRequest):
    if not client.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not set")

    # Get client IP and check session limits (disabled for testing)
    client_ip = get_client_ip(request)
    # if not check_session_limits(client_ip):
    #     raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    try:
        # Filter and validate messages
        filtered_messages = filter_system_messages(chat_request.messages)
        
        if not filtered_messages:
            raise HTTPException(status_code=400, detail="No valid messages provided")

        # Additional safety: limit total tokens
        total_chars = sum(len(msg["content"]) for msg in filtered_messages)
        if total_chars > 20000:
            raise HTTPException(status_code=400, detail="Request too large")

        # Return streaming response
        return StreamingResponse(
            generate_stream(filtered_messages),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        raise HTTPException(status_code=500, detail="Failed to process request")

# Add a non-streaming endpoint for fallback
@app.post("/api/chat-simple")
@limiter.limit("100/minute")
async def chat_simple(request: Request, chat_request: ChatRequest):
    """Non-streaming version for testing"""
    if not client.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not set")

    # Get client IP and check session limits (disabled for testing)
    client_ip = get_client_ip(request)
    # if not check_session_limits(client_ip):
    #     raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    try:
        filtered_messages = filter_system_messages(chat_request.messages)
        
        if not filtered_messages:
            raise HTTPException(status_code=400, detail="No valid messages provided")

        total_chars = sum(len(msg["content"]) for msg in filtered_messages)
        if total_chars > 5000:
            raise HTTPException(status_code=400, detail="Request too large")

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=filtered_messages,
            max_tokens=1000,
            temperature=0.7
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

