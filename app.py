from flask import Flask, jsonify, request
import requests
import json
from datetime import datetime

app = Flask(__name__)

# ==================== CONFIGURATION ====================
API_URL = "https://api.pepecards2f7z1qtyyg.top/v1/goods/lists"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "lang": "en",
    "origin": "https://api.pepecards2f7z1qtyyg.top",
    "referer": "https://api.pepecards2f7z1qtyyg.top/",
    "token": "f551e65b-4599-4789-a450-551b3b81f5bf",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ==================== COUNTRY FLAGS ====================
COUNTRY_FLAGS = {
    "PH": "🇵🇭", "US": "🇺🇸", "GB": "🇬🇧", "FR": "🇫🇷", "DE": "🇩🇪",
    "IT": "🇮🇹", "ES": "🇪🇸", "PT": "🇵🇹", "NL": "🇳🇱", "BE": "🇧🇪",
    "IE": "🇮🇪", "TR": "🇹🇷", "AR": "🇦🇷", "BR": "🇧🇷", "MX": "🇲🇽",
    "CA": "🇨🇦", "AU": "🇦🇺", "IN": "🇮🇳", "JP": "🇯🇵", "CN": "🇨🇳",
    "RU": "🇷🇺", "ZA": "🇿🇦", "NG": "🇳🇬", "EG": "🇪🇬", "SA": "🇸🇦",
    "AE": "🇦🇪", "SG": "🇸🇬", "MY": "🇲🇾", "ID": "🇮🇩", "TH": "🇹🇭",
    "VN": "🇻🇳", "KR": "🇰🇷", "PK": "🇵🇰", "BD": "🇧🇩", "KE": "🇰🇪"
}

# ==================== SAFE GET FUNCTION ====================
def safe_get(obj, *keys, default="N/A"):
    """Safely get nested dictionary values"""
    for key in keys:
        try:
            if obj is None:
                return default
            obj = obj.get(key, default) if isinstance(obj, dict) else default
        except (AttributeError, TypeError):
            return default
    return obj if obj is not None else default

def safe_card_value(card, *keys, default="N/A"):
    """Safely get value from card object"""
    try:
        value = card
        for key in keys:
            if value is None:
                return default
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value if value is not None else default
    except (AttributeError, TypeError):
        return default

# ==================== API FUNCTIONS ====================
def fetch_cards(bin_number, page=1, page_size=10):
    """Fetch cards from API"""
    payload = {
        "page": page,
        "pageSize": page_size,
        "bins": bin_number
    }
    
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ResCode") == 1:
                return data.get("ResData", {})
        return None
    except Exception as e:
        print(f"API Error: {e}")
        return None

def process_cards_data(card_data, bin_number):
    """Process and organize card data with analysis"""
    if not card_data or not card_data.get("data"):
        return None
    
    cards = card_data.get("data", [])
    
    # Filter out None cards
    cards = [c for c in cards if c is not None]
    
    if not cards:
        return None
    
    total = card_data.get("total", 0)
    current_page = int(card_data.get("current_page", 1))
    last_page = int(card_data.get("last_page", 1))
    
    # ========== PRICE ANALYSIS ==========
    prices = []
    for card in cards:
        try:
            price = float(safe_card_value(card, "price", default="0"))
            if price > 0:
                prices.append(price)
        except (ValueError, TypeError):
            continue
    
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0
    avg_price = round(sum(prices) / len(prices), 2) if prices else 0
    
    # ========== REFUNDABLE ANALYSIS ==========
    refundable = [c for c in cards if safe_card_value(c, "is_refund", default=0) == 1]
    non_refundable = [c for c in cards if safe_card_value(c, "is_refund", default=0) == 0]
    
    # ========== STOCK ANALYSIS ==========
    in_cart = [c for c in cards if safe_card_value(c, "in_cart", default=0) == 1]
    available = [c for c in cards if safe_card_value(c, "in_cart", default=0) == 0]
    
    # ========== BANK ANALYSIS ==========
    banks = {}
    for card in cards:
        bank_name = safe_card_value(card, "bankinfo", "bank_name", default="Unknown")
        if bank_name not in banks:
            banks[bank_name] = 0
        banks[bank_name] += 1
    
    # ========== SELLER ANALYSIS ==========
    sellers = {}
    for card in cards:
        seller = safe_card_value(card, "baseinfo", "seller_nickname", default="Unknown")
        if seller not in sellers:
            sellers[seller] = 0
        sellers[seller] += 1
    
    # ========== NEWEST BASE ==========
    newest_base = None
    if cards:
        first_card = cards[0]
        newest_base = {
            "id": safe_card_value(first_card, "id", default="N/A"),
            "name": safe_card_value(first_card, "baseinfo", "name", default="N/A"),
            "seller": safe_card_value(first_card, "baseinfo", "seller_nickname", default="N/A"),
            "sname": safe_card_value(first_card, "sname", default="N/A"),
            "price": safe_card_value(first_card, "price", default="N/A")
        }
    
    # ========== FORMAT CARDS WITH FLAGS ==========
    formatted_cards = []
    for card in cards:
        country_code = safe_card_value(card, "countryinfo", "code", default="")
        flag = COUNTRY_FLAGS.get(country_code, "🌍")
        
        formatted_cards.append({
            "id": safe_card_value(card, "id", default="N/A"),
            "bin": safe_card_value(card, "bin", default="N/A"),
            "price": float(safe_card_value(card, "price", default="0")),
            "currency": "USD",
            "type": safe_card_value(card, "type", default="N/A"),
            "network": safe_card_value(card, "typeinfo", "name", default="N/A"),
            "bank": safe_card_value(card, "bankinfo", "bank_name", default="N/A"),
            "city": safe_card_value(card, "city", default="N/A"),
            "state": safe_card_value(card, "state", default="N/A"),
            "country": safe_card_value(card, "countryinfo", "country_name", default="N/A"),
            "country_code": country_code,
            "flag": flag,
            "seller": safe_card_value(card, "baseinfo", "seller_nickname", default="N/A"),
            "in_cart": safe_card_value(card, "in_cart", default=0) == 1,
            "is_refundable": safe_card_value(card, "is_refund", default=0) == 1,
            "discount": float(safe_card_value(card, "nock_discount", default="0")),
            "has_email": safe_card_value(card, "email", default=False) == True,
            "has_phone": safe_card_value(card, "phone", default=False) == True,
            "has_address": safe_card_value(card, "full_address", default=False) == True,
            "has_zip": safe_card_value(card, "zip", default=False) == True
        })
    
    # ========== RETURN COMPLETE DATA ==========
    return {
        "bin": bin_number,
        "total_cards": total,
        "current_page": current_page,
        "last_page": last_page,
        "fetch_timestamp": datetime.now().isoformat(),
        "status": "success",
        "message": f"Found {len(cards)} cards for BIN {bin_number}",
        
        # ========== SUMMARY PEHLE ==========
        "summary": {
            "price_analysis": {
                "min_price": min_price,
                "max_price": max_price,
                "avg_price": avg_price,
                "total_cards_analyzed": len(prices)
            },
            "refundable": {
                "yes": len(refundable),
                "no": len(non_refundable)
            },
            "stock_status": {
                "available": len(available),
                "in_cart": len(in_cart)
            },
            "banks": banks,
            "sellers": sellers,
            "newest_base": newest_base
        },
        
        # ========== CARDS BAAD MEIN ==========
        "cards": formatted_cards
    }

# ==================== API ENDPOINTS ====================

@app.route('/search/<bin_number>', methods=['GET'])
def search_bin(bin_number):
    """Search by BIN only"""
    if not bin_number.isdigit() or len(bin_number) < 6:
        return jsonify({
            "error": "Invalid BIN number",
            "message": "BIN must be 6-8 digits",
            "status": 400
        }), 400
    
    data = fetch_cards(bin_number, page=1)
    if not data:
        return jsonify({
            "error": "No data found",
            "message": f"No cards found for BIN {bin_number}",
            "status": 404
        }), 404
    
    processed_data = process_cards_data(data, bin_number)
    
    if not processed_data:
        return jsonify({
            "error": "No valid cards found",
            "message": f"No valid cards found for BIN {bin_number}",
            "status": 404
        }), 404
    
    return jsonify(processed_data)


@app.route('/search/<bin_number>/<int:page>', methods=['GET'])
def search_bin_page(bin_number, page):
    """Search by BIN with page number"""
    if not bin_number.isdigit() or len(bin_number) < 6:
        return jsonify({
            "error": "Invalid BIN number",
            "message": "BIN must be 6-8 digits",
            "status": 400
        }), 400
    
    if page < 1:
        return jsonify({
            "error": "Invalid page number",
            "message": "Page must be >= 1",
            "status": 400
        }), 400
    
    data = fetch_cards(bin_number, page=page)
    if not data:
        return jsonify({
            "error": "No data found",
            "message": f"No cards found for BIN {bin_number} on page {page}",
            "status": 404
        }), 404
    
    processed_data = process_cards_data(data, bin_number)
    
    if not processed_data:
        return jsonify({
            "error": "No valid cards found",
            "message": f"No valid cards found for BIN {bin_number} on page {page}",
            "status": 404
        }), 404
    
    return jsonify(processed_data)


@app.route('/search/<bin_number>/all', methods=['GET'])
def search_all_pages(bin_number):
    """Fetch all pages for a BIN (max 10 pages)"""
    if not bin_number.isdigit() or len(bin_number) < 6:
        return jsonify({
            "error": "Invalid BIN number",
            "message": "BIN must be 6-8 digits",
            "status": 400
        }), 400
    
    # First fetch to get total pages
    first_page = fetch_cards(bin_number, page=1)
    if not first_page:
        return jsonify({
            "error": "No data found",
            "message": f"No cards found for BIN {bin_number}",
            "status": 404
        }), 404
    
    total_pages = int(first_page.get("last_page", 1))
    all_cards = []
    
    # Fetch all pages (max 10 pages to avoid timeout)
    max_pages = min(total_pages, 10)
    for page in range(1, max_pages + 1):
        data = fetch_cards(bin_number, page=page)
        if data and data.get("data"):
            cards = data.get("data", [])
            if cards:
                all_cards.extend(cards)
    
    if not all_cards:
        return jsonify({
            "error": "No cards found",
            "message": f"No cards found for BIN {bin_number}",
            "status": 404
        }), 404
    
    # Create combined response
    combined_data = {
        "current_page": 1,
        "last_page": max_pages,
        "total": len(all_cards),
        "data": all_cards
    }
    
    processed_data = process_cards_data(combined_data, bin_number)
    
    if not processed_data:
        return jsonify({
            "error": "No valid cards found",
            "message": f"No valid cards found for BIN {bin_number}",
            "status": 404
        }), 404
    
    return jsonify(processed_data)


@app.route('/api/status', methods=['GET'])
def status():
    """Check API status"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.2",
        "endpoints": {
            "/search/{bin}": "Search by BIN (summary first)",
            "/search/{bin}/{page}": "Search by BIN with page",
            "/search/{bin}/all": "Fetch all pages (max 10)"
        }
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "status": 404
    }), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "error": "Internal server error",
        "status": 500
    }), 500


# ==================== MAIN ====================
if __name__ == '__main__':
    print("🚀 Starting CC Shop API...")
    print("📍 Base URL: http://127.0.0.1:5000")
    print("")
    print("📌 Available Endpoints:")
    print("  GET /search/{bin}")
    print("  GET /search/{bin}/{page}")
    print("  GET /search/{bin}/all")
    print("  GET /api/status")
    print("")
    print("🔍 Example:")
    print("  http://127.0.0.1:5000/search/521069")
    print("  http://127.0.0.1:5000/search/521069/2")
    print("  http://127.0.0.1:5000/search/521069/all")
    print("")
    app.run(debug=True, host='0.0.0.0', port=5000)
