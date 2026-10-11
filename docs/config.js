// ============================================================
//   🌶️ DARK MARKET — Configuration
// ============================================================

// IMPORTANT: Update this to your backend API URL
// For local development: http://localhost:8000
// For production: https://your-backend-domain.com

const API_CONFIG = {
    // Change this to your backend API endpoint
    API_URL: 'https://dark-market-api.onrender.com',
    
    // WebSocket URL (ws:// for http, wss:// for https)
    WS_URL: 'wss://dark-market-api.onrender.com/ws'
};

// Validate API configuration
if (!API_CONFIG.API_URL || API_CONFIG.API_URL === 'https://your-backend-domain.com') {
    console.warn('[!] API_URL not configured. Please update config.js');
}