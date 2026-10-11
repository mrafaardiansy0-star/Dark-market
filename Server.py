#!/usr/bin/env python3
# ============================================================
#   🌶️ DARK MARKET — Backend Server
#   FastAPI + WebSocket + SQLite
# ============================================================

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import hashlib
import secrets
import json
import time
import os
import jwt
from datetime import datetime, timedelta

# ============================================================
#   CONFIG
# ============================================================

SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
DB_FILE = "darkmarket.db"
HOST = "0.0.0.0"
PORT = 8000

# ============================================================
#   DATABASE
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            wallet REAL DEFAULT 0,
            created_at TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT,
            image TEXT,
            stock INTEGER DEFAULT 1,
            created_at TEXT,
            FOREIGN KEY (seller_id) REFERENCES users(id)
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            product_id INTEGER,
            created_at TEXT,
            read INTEGER DEFAULT 0,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id INTEGER NOT NULL,
            seller_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            total REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            FOREIGN KEY (buyer_id) REFERENCES users(id),
            FOREIGN KEY (seller_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("[+] Database initialized")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================
#   AUTH
# ============================================================

def hash_password(password: str) -> str:
    return hashlib.sha256((password + SECRET_KEY).encode()).hexdigest()

def create_token(user_id: int, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        return None

# ============================================================
#   MODELS
# ============================================================

class RegisterReq(BaseModel):
    username: str
    password: str
    email: Optional[str] = ""

class LoginReq(BaseModel):
    username: str
    password: str

class ProductReq(BaseModel):
    title: str
    description: str
    price: float
    category: str = "general"
    stock: int = 1

class MessageReq(BaseModel):
    receiver_id: int
    content: str
    product_id: Optional[int] = None

class OrderReq(BaseModel):
    product_id: int
    quantity: int = 1

# ============================================================
#   FASTAPI APP
# ============================================================

app = FastAPI(title="Dark Market")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
#   AUTH ENDPOINTS
# ============================================================

@app.post("/api/register")
def register(req: RegisterReq):
    conn = get_db()
    c = conn.cursor()
    
    existing = c.execute("SELECT id FROM users WHERE username = ?", (req.username,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(400, "Username already taken")
    
    c.execute(
        "INSERT INTO users (username, password_hash, email, wallet, created_at) VALUES (?, ?, ?, ?, ?)",
        (req.username, hash_password(req.password), req.email, 1000.0, datetime.utcnow().isoformat())
    )
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    
    token = create_token(user_id, req.username)
    return {"token": token, "user_id": user_id, "username": req.username, "wallet": 1000.0}

@app.post("/api/login")
def login(req: LoginReq):
    conn = get_db()
    c = conn.cursor()
    user = c.execute(
        "SELECT id, username, password_hash, wallet FROM users WHERE username = ?",
        (req.username,)
    ).fetchone()
    conn.close()
    
    if not user or user["password_hash"] != hash_password(req.password):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_token(user["id"], user["username"])
    return {"token": token, "user_id": user["id"], "username": user["username"], "wallet": user["wallet"]}

@app.get("/api/me")
def me(token: str):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    
    conn = get_db()
    user = conn.execute(
        "SELECT id, username, email, wallet FROM users WHERE id = ?",
        (payload["user_id"],)
    ).fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(404, "User not found")
    return dict(user)

# ============================================================
#   MARKETPLACE ENDPOINTS
# ============================================================

@app.get("/api/products")
def list_products(category: Optional[str] = None, search: Optional[str] = None):
    conn = get_db()
    query = """
        SELECT p.id, p.title, p.description, p.price, p.category, p.stock, 
               p.created_at, u.username as seller, p.seller_id
        FROM products p
        JOIN users u ON p.seller_id = u.id
        WHERE p.stock > 0
    """
    params = []
    
    if category:
        query += " AND p.category = ?"
        params.append(category)
    if search:
        query += " AND (p.title LIKE ? OR p.description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    query += " ORDER BY p.created_at DESC"
    products = conn.execute(query, params).fetchall()
    conn.close()
    
    return [dict(p) for p in products]

@app.post("/api/products")
def create_product(req: ProductReq, token: str):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO products (seller_id, title, description, price, category, stock, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (payload["user_id"], req.title, req.description, req.price, req.category, req.stock, datetime.utcnow().isoformat())
    )
    conn.commit()
    product_id = c.lastrowid
    conn.close()
    
    return {"id": product_id, "status": "created"}

@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    conn = get_db()
    product = conn.execute("""
        SELECT p.*, u.username as seller
        FROM products p
        JOIN users u ON p.seller_id = u.id
        WHERE p.id = ?
    """, (product_id,)).fetchone()
    conn.close()
    
    if not product:
        raise HTTPException(404, "Product not found")
    return dict(product)

# ============================================================
#   ORDER ENDPOINTS
# ============================================================

@app.post("/api/orders")
def create_order(req: OrderReq, token: str):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    
    conn = get_db()
    c = conn.cursor()
    
    product = c.execute("SELECT * FROM products WHERE id = ?", (req.product_id,)).fetchone()
    if not product:
        conn.close()
        raise HTTPException(404, "Product not found")
    
    if product["seller_id"] == payload["user_id"]:
        conn.close()
        raise HTTPException(400, "Can't buy your own product")
    
    total = product["price"] * req.quantity
    
    buyer = c.execute("SELECT wallet FROM users WHERE id = ?", (payload["user_id"],)).fetchone()
    if buyer["wallet"] < total:
        conn.close()
        raise HTTPException(400, "Insufficient wallet balance")
    
    # transfer
    c.execute("UPDATE users SET wallet = wallet - ? WHERE id = ?", (total, payload["user_id"]))
    c.execute("UPDATE users SET wallet = wallet + ? WHERE id = ?", (total, product["seller_id"]))
    c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (req.quantity, req.product_id))
    
    c.execute(
        """INSERT INTO orders (buyer_id, seller_id, product_id, quantity, total, status, created_at)
           VALUES (?, ?, ?, ?, ?, 'paid', ?)""",
        (payload["user_id"], product["seller_id"], req.product_id, req.quantity, total, datetime.utcnow().isoformat())
    )
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return {"order_id": order_id, "status": "paid", "total": total}

@app.get("/api/orders")
def list_orders(token: str):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    
    conn = get_db()
    orders = conn.execute("""
        SELECT o.*, p.title as product_title, 
               ub.username as buyer, us.username as seller
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN users ub ON o.buyer_id = ub.id
        JOIN users us ON o.seller_id = us.id
        WHERE o.buyer_id = ? OR o.seller_id = ?
        ORDER BY o.created_at DESC
    """, (payload["user_id"], payload["user_id"])).fetchall()
    conn.close()
    
    return [dict(o) for o in orders]

# ============================================================
#   CHAT HISTORY
# ============================================================

@app.get("/api/messages/{other_user_id}")
def get_messages(other_user_id: int, token: str):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    
    my_id = payload["user_id"]
    conn = get_db()
    messages = conn.execute("""
        SELECT m.*, u.username as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.created_at ASC
        LIMIT 100
    """, (my_id, other_user_id, other_user_id, my_id)).fetchall()
    conn.close()
    
    return [dict(m) for m in messages]

@app.get("/api/chats")
def list_chats(token: str):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    
    my_id = payload["user_id"]
    conn = get_db()
    chats = conn.execute("""
        SELECT DISTINCT 
            CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END as other_id,
            u.username as other_name
        FROM messages m
        JOIN users u ON u.id = CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END
        WHERE sender_id = ? OR receiver_id = ?
    """, (my_id, my_id, my_id, my_id)).fetchall()
    conn.close()
    
    return [dict(c) for c in chats]

# ============================================================
#   WEBSOCKET — REAL-TIME CHAT
# ============================================================

class ConnectionManager:
    def __init__(self):
        self.active: dict[int, WebSocket] = {}
    
    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.active[user_id] = ws
        print(f"[+] User {user_id} connected")
    
    def disconnect(self, user_id: int):
        if user_id in self.active:
            del self.active[user_id]
            print(f"[-] User {user_id} disconnected")
    
    async def send_to(self, user_id: int, message: dict):
        if user_id in self.active:
            try:
                await self.active[user_id].send_json(message)
                return True
            except:
                pass
        return False
    
    async def broadcast(self, message: dict):
        for uid, ws in list(self.active.items()):
            try:
                await ws.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    token = ws.query_params.get("token")
    payload = verify_token(token) if token else None
    
    if not payload:
        await ws.close(code=4001)
        return
    
    user_id = payload["user_id"]
    username = payload["username"]
    await manager.connect(user_id, ws)
    
    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")
            
            if action == "message":
                receiver_id = data.get("receiver_id")
                content = data.get("content")
                product_id = data.get("product_id")
                
                if not receiver_id or not content:
                    continue
                
                # simpen ke db
                conn = get_db()
                c = conn.cursor()
                c.execute(
                    """INSERT INTO messages (sender_id, receiver_id, content, product_id, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, receiver_id, content, product_id, datetime.utcnow().isoformat())
                )
                conn.commit()
                msg_id = c.lastrowid
                conn.close()
                
                msg_data = {
                    "type": "message",
                    "id": msg_id,
                    "sender_id": user_id,
                    "sender_name": username,
                    "receiver_id": receiver_id,
                    "content": content,
                    "product_id": product_id,
                    "created_at": datetime.utcnow().isoformat(),
                }
                
                # kirim ke sender
                await manager.send_to(user_id, msg_data)
                # kirim ke receiver
                await manager.send_to(receiver_id, msg_data)
            
            elif action == "typing":
                receiver_id = data.get("receiver_id")
                await manager.send_to(receiver_id, {
                    "type": "typing",
                    "user_id": user_id,
                    "username": username,
                })
            
            elif action == "ping":
                await ws.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"[!] WS error: {e}")
        manager.disconnect(user_id)

# ============================================================
#   SERVE FRONTEND
# ============================================================

@app.get("/")
def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# ============================================================
#   RUN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    init_db()
    print(f"""
╔══════════════════════════════════════════════════╗
║  🌶️ DARK MARKET — Server Running                ║
║  URL: http://{HOST}:{PORT}                      ║
╚══════════════════════════════════════════════════╝
""")
    uvicorn.run(app, host=HOST, port=PORT)
