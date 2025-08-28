# Manual Render Deployment

Instead of using Blueprint, deploy each service separately:

## 1. Deploy Backend (Web Service)
1. Go to Render Dashboard → "New" → "Web Service"
2. Connect GitHub repo: `YehudaNevo/sugya-app`
3. Settings:
   - **Name**: `sugya-app-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && python main.py`
   - **Environment Variables**: Add `OPENAI_API_KEY` with your API key

## 2. Deploy Frontend (Static Site)
1. Go to Render Dashboard → "New" → "Static Site"  
2. Connect GitHub repo: `YehudaNevo/sugya-app`
3. Settings:
   - **Name**: `sugya-app-frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
   - **Environment Variables**: Add `VITE_API_URL` with your backend URL (e.g., `https://sugya-app-backend.onrender.com`)

This approach is more reliable than Blueprint deployment.