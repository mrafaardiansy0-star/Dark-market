# 🌶️ Dark Market — GitHub Pages Frontend

This is the **frontend only** version deployed on GitHub Pages.

## 🌐 Live URL

```
https://mrafaardiansy0-star.github.io/Dark-market/
```

## ⚙️ Configuration

The frontend connects to a backend API. Before using, update the API URL in `docs/config.js`:

```javascript
const API_CONFIG = {
    API_URL: 'https://your-backend-api.com',  // <-- Change this
    WS_URL: 'wss://your-backend-api.com/ws'
};
```

## 🚀 Backend Setup

You need to deploy the backend separately. We recommend **Render** (free tier available):

### Quick Backend Deployment on Render

1. Go to [render.com](https://render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `python server.py`
6. Add environment variables:
   - `PORT`: `8000`
7. Deploy!

You'll get a URL like: `https://dark-market-api.onrender.com`

Update `docs/config.js` with that URL.

## 📝 Features

- ✅ User registration & login (JWT)
- ✅ Marketplace (browse, sell, buy products)
- ✅ Real-time chat (WebSocket)
- ✅ Wallet system
- ✅ Order management
- ✅ Dark theme UI

## 📂 Files

- `docs/index.html` — Main HTML page with inline CSS
- `docs/config.js` — API configuration (UPDATE THIS!)
- `docs/app.js` — Frontend JavaScript logic
- `Server.py` — Backend FastAPI server (deploy separately)

## 🔧 Local Testing

```bash
# Terminal 1: Run backend
python server.py

# Terminal 2: Open frontend in browser
open http://localhost:8000
```

## ⚠️ Important Notes

- GitHub Pages only hosts **static files**. The backend must run on a separate server.
- Free Render deployments may take a few seconds to start.
- WebSocket connections require a live backend server.

---

**Need help?** Check `config.js` for API configuration details.