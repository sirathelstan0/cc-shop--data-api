import os
from flask import Flask, jsonify, request
import requests
import random
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# ---------- Price logic ----------
def get_bin_price(bin_number):
    digits = [int(d) for d in str(bin_number) if d.isdigit()]
    if not digits:
        return "$0.00"
    total = sum(digit * (index + 3) for index, digit in enumerate(digits))
    price = 2 + (total % 101) / 100
    return f"${price:.2f}"

# ---------- Validation ----------
def is_valid_bin(bin_number):
    if not bin_number.isdigit():
        return False, "BIN must contain only digits"
    if len(bin_number) != 6:
        return False, "BIN must be exactly 6 digits"
    if bin_number[0] not in ("2", "4", "5"):
        return False, "Only VISA and MASTERCARD BINs are supported"
    return True, None

# ---------- BIN lookup ----------
BIN_API = "https://bins.antipublic.cc/bins/{bin}"

@lru_cache(maxsize=4096)
def fetch_bin_data(bin_number):
    try:
        r = requests.get(BIN_API.format(bin=bin_number), timeout=6)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None

# ---------- Random BIN generator ----------
def random_visa_bin():
    return "4" + "".join(str(random.randint(0, 9)) for _ in range(5))

def random_mastercard_bin():
    first = random.choice(["5", "2"])
    return first + "".join(str(random.randint(0, 9)) for _ in range(5))

def random_bin():
    return random.choice([random_visa_bin, random_mastercard_bin])()

def fetch_one_card(bin_num):
    data = fetch_bin_data(bin_num)
    if not data:
        return None
    brand = (data.get("brand") or "").upper()
    if brand not in ("VISA", "MASTERCARD"):
        return None
    price = get_bin_price(bin_num)
    data["price"] = price
    data["amount"] = price
    return data

def get_random_cards(count=10, max_workers=20, deadline_seconds=4.0):
    import time
    start = time.time()
    cards = []
    seen = set()

    candidate_pool = []
    while len(candidate_pool) < count * 4:
        b = random_bin()
        if b not in seen:
            seen.add(b)
            candidate_pool.append(b)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_one_card, b): b for b in candidate_pool}
        for fut in as_completed(futures, timeout=deadline_seconds + 2):
            if time.time() - start > deadline_seconds and len(cards) >= count // 2:
                break
            try:
                result = fut.result(timeout=0.1)
            except Exception:
                continue
            if result:
                cards.append(result)
                if len(cards) >= count:
                    break
    return cards[:count]

# ---------- Endpoints ----------
@app.route("/bins/<bin_number>", methods=["GET"])
def bin_with_price(bin_number):
    ok, reason = is_valid_bin(bin_number)
    if not ok:
        return jsonify({"status": "not_found", "message": reason, "bin": bin_number}), 404

    data = fetch_bin_data(bin_number)
    if not data:
        return jsonify({"status": "not_found", "message": "BIN not found", "bin": bin_number}), 404

    brand = (data.get("brand") or "").upper()
    if brand not in ("VISA", "MASTERCARD"):
        return jsonify({
            "status": "not_found",
            "message": "Only VISA and MASTERCARD BINs are supported",
            "bin": bin_number
        }), 404

    price = get_bin_price(bin_number)
    data["price"] = price
    data["amount"] = price
    return jsonify(data)

@app.route("/explore", methods=["GET"])
def explore():
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    if page < 1:
        page = 1

    cards = get_random_cards(count=10)
    return jsonify({
        "status": "ok",
        "page": page,
        "count": len(cards),
        "cards": cards
    })

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "message": "BIN API is running",
        "endpoints": ["/bins/<bin>", "/explore", "/doc"]
    })

# ---------- /doc (same as before) ----------
@app.route("/doc", methods=["GET"])
def api_docs():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BIN API — Documentation</title>
<style>
  :root { --bg:#0d1117; --card:#161b22; --border:#30363d; --txt:#c9d1d9; --muted:#8b949e; --accent:#58a6ff; --green:#3fb950; --red:#f85149; --yellow:#d29922; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--txt); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; padding: 2rem 1rem; }
  .container { max-width: 900px; margin: 0 auto; }
  h1 { font-size: 2rem; margin-bottom: 0.5rem; color: #fff; }
  .subtitle { color: var(--muted); margin-bottom: 2rem; }
  .endpoint { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }
  .method-row { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap; }
  .method { font-weight: 700; font-size: 0.85rem; padding: 0.25rem 0.75rem; border-radius: 6px; background: #1f6feb; color: white; }
  .path { font-family: "SF Mono", Monaco, monospace; font-size: 1rem; color: var(--accent); }
  .desc { color: var(--muted); margin-bottom: 1rem; }
  .section-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin: 1rem 0 0.5rem; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
  th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; }
  code { font-family: "SF Mono", Monaco, monospace; background: #1f242c; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.85em; color: #ffa657; }
  pre { background: #0d1117; border: 1px solid var(--border); border-radius: 6px; padding: 1rem; overflow-x: auto; font-size: 0.85rem; font-family: "SF Mono", Monaco, monospace; color: var(--txt); }
  .try-btn { background: #238636; color: white; border: none; padding: 0.4rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }
  .try-btn:hover { background: #2ea043; }
  .response-box { margin-top: 0.75rem; display: none; }
  .response-box.show { display: block; }
  .status-ok { color: var(--green); }
  .status-err { color: var(--red); }
  .badge { display:inline-block; font-size:0.75rem; padding:0.15rem 0.5rem; border-radius:4px; background:#1f242c; color:var(--yellow); margin-left:0.5rem; }
</style>
</head>
<body>
<div class="container">
  <h1>💳 BIN API</h1>
  <p class="subtitle">VISA &amp; Mastercard BIN lookup with pricing. Only 6-digit BINs starting with 2, 4, or 5 are supported.</p>

  <div class="endpoint">
    <div class="method-row"><span class="method">GET</span><span class="path">/bins/{bin}</span><span class="badge">6-digit</span></div>
    <p class="desc">Look up a single BIN. Returns brand, bank, country, level, type and calculated price.</p>
    <div class="section-title">Path Parameters</div>
    <table><tr><th>Name</th><th>Type</th><th>Description</th></tr>
      <tr><td><code>bin</code></td><td>string</td><td>Exactly 6 digits. Must start with 2, 4 or 5.</td></tr></table>
    <div class="section-title">Example Request</div><pre>GET /bins/521068</pre>
    <div class="section-title">Example Response (200)</div>
    <pre>{
  "bin": "521068", "brand": "MASTERCARD", "country": "BO",
  "country_name": "BOLIVIA", "country_flag": "🇧🇴",
  "country_currencies": ["BOB"],
  "bank": "ADMINISTRADORA DE TARJETAS DE CREDITO, (A.T.C.), S.A.",
  "level": "BLACK", "type": "CREDIT",
  "price": "$2.50", "amount": "$2.50"
}</pre>
    <div class="section-title">Not Found (404)</div>
    <pre>{"status":"not_found","message":"BIN must be exactly 6 digits","bin":"12345"}</pre>
    <button class="try-btn" onclick="tryBins()">Try it</button>
    <div id="bins-resp" class="response-box"></div>
  </div>

  <div class="endpoint">
    <div class="method-row"><span class="method">GET</span><span class="path">/explore</span><span class="badge">random</span></div>
    <p class="desc">Returns 10 random valid VISA/Mastercard cards with prices, fetched in parallel.</p>
    <div class="section-title">Query Parameters</div>
    <table><tr><th>Name</th><th>Type</th><th>Required</th><th>Description</th></tr>
      <tr><td><code>page</code></td><td>integer</td><td>no</td><td>Page number (default 1).</td></tr></table>
    <div class="section-title">Example Request</div><pre>GET /explore?page=1</pre>
    <div class="section-title">Example Response (200)</div>
    <pre>{
  "status": "ok", "page": 1, "count": 10,
  "cards": [
    { "bin": "521068", "brand": "MASTERCARD", "price": "$2.50", ... },
    { "bin": "414027", "brand": "VISA", "price": "$2.88", ... }
  ]
}</pre>
    <button class="try-btn" onclick="tryExplore()">Try it</button>
    <div id="explore-resp" class="response-box"></div>
  </div>

  <p style="text-align:center; color:var(--muted); margin-top:2rem; font-size:0.85rem;">Built with Flask · Data source: bins.antipublic.cc</p>
</div>
<script>
async function callApi(url, targetId) {
  const box = document.getElementById(targetId);
  box.classList.add("show");
  box.innerHTML = "<pre>Loading...</pre>";
  try {
    const res = await fetch(url);
    const text = await res.text();
    const cls = res.ok ? "status-ok" : "status-err";
    box.innerHTML = `<div class="${cls}">Status: ${res.status}</div><pre>${text}</pre>`;
  } catch (e) {
    box.innerHTML = `<div class="status-err">Error: ${e.message}</div>`;
  }
}
function tryBins() {
  const bin = prompt("Enter 6-digit BIN (e.g. 521068):", "521068");
  if (bin) callApi("/bins/" + bin, "bins-resp");
}
function tryExplore() { callApi("/explore", "explore-resp"); }
</script>
</body>
</html>"""
    return html


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
