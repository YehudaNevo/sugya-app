# Sugya App

A digital chavruta (study partner) application for learning the Talmudic topic of "ייאוש שלא מדעת" (despair without knowledge).

## Architecture

- **Backend**: FastAPI Python server with OpenAI integration
- **Frontend**: React with Vite for the user interface

## Setup

### Backend
1. Navigate to the backend directory: `cd backend`
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Create `.env` file with your OpenAI API key: `OPENAI_API_KEY=your_key_here`
6. Run: `python main.py`

### Frontend
1. Install dependencies: `npm install`
2. Create `.env` file: `VITE_API_URL=http://localhost:8000`
3. Run development server: `npm run dev`

## Deployment

This app is configured for easy deployment on Render using the included `render.yaml` configuration.
