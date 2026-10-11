// ============================================================
//   🌶️ DARK MARKET — Frontend Logic
// ============================================================

const API = window.location.origin;
let state = {
    token: localStorage.getItem("token"),
    user: null,
    ws: null,
    currentChat: null,
    currentTab: "market",
    products: [],
    chats: [],
};

let authMode = "login";

// ============================================================
//   AUTH
// ============================================================

function switchTab(mode) {
    authMode = mode;
    document.getElementById("tabLogin").classList.toggle("active", mode === "login");
    document.getElementById("tabRegister").classList.toggle("active", mode === "register");
    document.getElementById("authEmail").classList.toggle("hidden", mode === "login");
    document.getElementById("authBtn").textContent = mode === "login" ? "LOGIN" : "REGISTER";
}

async function doAuth() {
    const username = document.getElementById("authUsername").value.trim();
    const password = document.getElementById("authPassword").value;
    const email = document.getElementById("authEmail").value.trim();
    
    if (!username || !password) return toast("Isi username + password");
    
    const endpoint = authMode === "login" ? "/api/login" : "/api/register";
    const body = authMode === "login" ? { username, password } : { username, password, email };
    
    try {
        const r = await fetch(API + endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await r.json();
        if (!r.ok) return toast(data.detail || "Error");
        
        state.token = data.token;
        state.user = data;
        localStorage.setItem("token", data.token);
        enterApp();
    } catch (e) {
        toast("Error: " + e.message);
    }
}

async function checkAuth() {
    if (!state.token) return;
    try {
        const r = await fetch(API + "/api/me?token=" + state.token);
        if (!r.ok) {
            state.token = null;
            localStorage.removeItem("token");
            return;
        }
        state.user = await r.json();
        enterApp();
    } catch (e) {}
}

function enterApp() {
    document.getElementById("authScreen").classList.add("hidden");
    document.getElementById("appScreen").classList.remove("hidden");
    document.getElementById("userName").textContent = state.user.username;
    document.getElementById("userWallet").textContent = "$" + state.user.wallet.toFixed(2);
    connectWS();
    showTab("market");
}

function logout() {
    localStorage.removeItem("token");
    location.reload();
}

// ============================================================
//   WEBSOCKET
// ============================================================

function connectWS() {
    if (!state.token) return;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${proto}//${window.location.host}/ws?token=${state.token}`;
    state.ws = new WebSocket(wsUrl);
    
    state.ws.onopen = () => console.log("[+] WS connected");
    
    state.ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "message") {
            if (state.currentChat && (msg.sender_id === state.currentChat.other_id || msg.receiver_id === state.currentChat.other_id)) {
                appendMessage(msg);
            }
            loadChats();
        }
    };
    
    state.ws.onclose = () => {
        console.log("[-] WS closed, reconnecting...");
        setTimeout(connectWS, 3000);
    };
}

// ============================================================
//   TAB NAVIGATION
// ============================================================

function showTab(tab, btn) {
    state.currentTab = tab;
    document.querySelectorAll(".sidebar button").forEach(b => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
    
    if (tab === "market") loadMarket();
    else if (tab === "sell") showSellForm();
    else if (tab === "chat") loadChats();
    else if (tab === "orders") loadOrders();
    else if (tab === "wallet") showWallet();
}

// ============================================================
//   MARKET
// ============================================================

async function loadMarket() {
    const r = await fetch(API + "/api/products");
    state.products = await r.json();
    
    const main = document.getElementById("mainArea");
    if (state.products.length === 0) {
        main.innerHTML = '<div class="empty">Belum ada produk. Jual yang pertama!</div>';
        return;
    }
    
    main.innerHTML = `
        <div class="products-grid">
            ${state.products.map(p => `
                <div class="product-card" onclick="openProduct(${p.id})">
                    <div class="category">${p.category}</div>
                    <h3>${escapeHtml(p.title)}</h3>
                    <div class="desc">${escapeHtml(p.description || "")}</div>
                    <div class="price">$${p.price.toFixed(2)}</div>
                    <div class="seller">by ${escapeHtml(p.seller)} • stock: ${p.stock}</div>
                </div>
            `).join("")}
        </div>
    `;
}

async function openProduct(id) {
    const r = await fetch(API + "/api/products/" + id);
    const p = await r.json();
    
    document.getElementById("modalContent").innerHTML = `
        <h2>${escapeHtml(p.title)}</h2>
        <div class="category">${p.category}</div>
        <p style="color:var(--dim);font-size:12px;margin:12px 0;">${escapeHtml(p.description || "")}</p>
        <div class="price">$${p.price.toFixed(2)}</div>
        <p style="font-size:11px;color:var(--dim);">Seller: ${escapeHtml(p.seller)} • Stock: ${p.stock}</p>
        <div class="modal-actions">
            <button class="btn-buy" onclick="buyProduct(${p.id})">🛒 BELI</button>
            <button class="btn-chat" onclick="chatSeller(${p.seller_id}, ${p.id})">💬 CHAT</button>
            <button class="btn-close" onclick="closeModal()">TUTUP</button>
        </div>
    `;
    document.getElementById("modal").classList.remove("hidden");
}

async function buyProduct(id) {
    try {
        const r = await fetch(API + "/api/orders?token=" + state.token, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ product_id: id, quantity: 1 }),
        });
        const data = await r.json();
        if (!r.ok) return toast(data.detail || "Error");
        toast("✅ Berhasil beli! Total: $" + data.total);
        closeModal();
        loadMarket();
    } catch (e) {
        toast("Error: " + e.message);
    }
}

async function chatSeller(sellerId, productId) {
    closeModal();
    showTab("chat", document.querySelectorAll(".sidebar button")[2]);
    setTimeout(() => openChat(sellerId), 300);
}

// ============================================================
//   SELL
// ============================================================

function showSellForm() {
    document.getElementById("mainArea").innerHTML = `
        <div class="form-box">
            <h2>💰 JUAL PRODUK</h2>
            <input id="pTitle" placeholder="Nama produk">
            <textarea id="pDesc" placeholder="Deskripsi"></textarea>
            <input id="pPrice" type="number" placeholder="Harga (USD)" step="0.01">
            <input id="pCategory" placeholder="Kategori (general, digital, dll)">
            <input id="pStock" type="number" placeholder="Stock" value="1">
            <button onclick="submitProduct()">JUAL</button>
        </div>
    `;
}

async function submitProduct() {
    const title = document.getElementById("pTitle").value.trim();
    const description = document.getElementById("pDesc").value.trim();
    const price = parseFloat(document.getElementById("pPrice").value);
    const category = document.getElementById("pCategory").value.trim() || "general";
    const stock = parseInt(document.getElementById("pStock").value) || 1;
    
    if (!title || !price) return toast("Isi nama + harga");
    
    const r = await fetch(API + "/api/products?token=" + state.token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description, price, category, stock }),
    });
    const data = await r.json();
    if (!r.ok) return toast(data.detail || "Error");
    toast("✅ Produk berhasil dijual!");
    showTab("market", document.querySelectorAll(".sidebar button")[0]);
}

// ============================================================
//   CHAT
// ============================================================

async function loadChats() {
    const r = await fetch(API + "/api/chats?token=" + state.token);
    state.chats = await r.json();
    
    const main = document.getElementById("mainArea");
    main.innerHTML = `
        <div class="chat-container">
            <div class="chat-list" id="chatList">
                ${state.chats.length === 0 
                    ? '<div class="empty" style="padding:20px;font-size:11px;">Belum ada chat</div>'
                    : state.chats.map(c => `
                        <div class="chat-list-item" onclick="openChat(${c.other_id})">
                            ${escapeHtml(c.other_name)}
                        </div>
                    `).join("")
                }
            </div>
            <div class="chat-window" id="chatWindow">
                <div class="empty">Pilih chat</div>
            </div>
        </div>
    `;
}

async function openChat(otherId) {
    state.currentChat = { other_id: otherId };
    
    const r = await fetch(API + `/api/messages/${otherId}?token=` + state.token);
    const msgs = await r.json();
    
    document.getElementById("chatWindow").innerHTML = `
        <div class="chat-header" id="chatHeader">Chat</div>
        <div class="chat-messages" id="chatMessages"></div>
        <div class="chat-input">
            <input id="chatInput" placeholder="Ketik pesan..." onkeydown="if(event.key==='Enter')sendMessage()">
            <button onclick="sendMessage()">KIRIM</button>
        </div>
    `;
    
    msgs.forEach(m => appendMessage(m));
}

function appendMessage(m) {
    const box = document.getElementById("chatMessages");
    if (!box) return;
    const isMe = m.sender_id === state.user.user_id;
    const div = document.createElement("div");
    div.className = "msg " + (isMe ? "me" : "other");
    div.innerHTML = `${!isMe ? `<div class="sender">${escapeHtml(m.sender_name || "User")}</div>` : ""}${escapeHtml(m.content)}`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById("chatInput");
    const content = input.value.trim();
    if (!content || !state.ws || !state.currentChat) return;
    
    state.ws.send(JSON.stringify({
        action: "message",
        receiver_id: state.currentChat.other_id,
        content: content,
    }));
    input.value = "";
}

// ============================================================
//   ORDERS
// ============================================================

async function loadOrders() {
    const r = await fetch(API + "/api/orders?token=" + state.token);
    const orders = await r.json();
    
    document.getElementById("mainArea").innerHTML = `
        <h2 style="color:var(--accent);margin-bottom:16px;">📦 ORDERS</h2>
        ${orders.length === 0 
            ? '<div class="empty">Belum ada order</div>'
            : orders.map(o => `
                <div class="product-card" style="margin-bottom:12px;">
                    <h3>${escapeHtml(o.product_title)}</h3>
                    <div class="desc">Buyer: ${escapeHtml(o.buyer)} • Seller: ${escapeHtml(o.seller)}</div>
                    <div class="price">$${o.total.toFixed(2)}</div>
                    <div class="seller">Status: ${o.status} • ${new Date(o.created_at).toLocaleString()}</div>
                </div>
            `).join("")
        }
    `;
}

// ============================================================
//   WALLET
// ============================================================

async function showWallet() {
    const r = await fetch(API + "/api/me?token=" + state.token);
    const user = await r.json();
    state.user = user;
    document.getElementById("userWallet").textContent = "$" + user.wallet.toFixed(2);
    
    document.getElementById("mainArea").innerHTML = `
        <div class="form-box">
            <h2>💳 WALLET</h2>
            <div class="price" style="font-size:36px;">$${user.wallet.toFixed(2)}</div>
            <p style="color:var(--dim);font-size:12px;margin-top:16px;">
                Username: ${escapeHtml(user.username)}<br>
                Email: ${escapeHtml(user.email || "-")}
            </p>
        </div>
    `;
}

// ============================================================
//   MODAL + TOAST + UTILS
// ============================================================

function closeModal() {
    document.getElementById("modal").classList.add("hidden");
}

function toast(msg) {
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
}

function escapeHtml(s) {
    if (!s) return "";
    return String(s).replace(/[&<>"']/g, m => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[m]));
}

// ============================================================
//   INIT
// ============================================================

checkAuth();
