import requests
import hashlib
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# ================= CONFIG =================
APP_ID = "YD5038"
SECRET_KEY = "WdX2XVTDnV8dmpc2GMl4EaDW9lMH2DTT"
TELEGRAM_BOT_TOKEN = "8660649540:AAECvvBwKYk8vz6DXQSA82CNRe1dupqMnj4"

BASE_URL = "https://nexus-pay.onrender.com"
CALLBACK_URL = f"{BASE_URL}/lgpay_callback"

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# 🔥 MULTIPLE TRADE TYPES (AUTO TRY)
TRADE_TYPES = [
    "UPI",
    "UPI_IN",
    "INDIA",
    "INR",
    "PAYIN",
    "UPI_INDIA"
]


# ================= MEMORY =================
user_state = {}
orders = {}

# ================= SIGN =================
def generate_sign(data, key):
    data = {k: v for k, v in data.items() if v != "" and v is not None}
    sorted_data = dict(sorted(data.items()))
    stringA = "&".join([f"{k}={v}" for k, v in sorted_data.items()])
    stringA = f"{stringA}&key={key}"
    return hashlib.md5(stringA.encode()).hexdigest().upper()

# ================= TELEGRAM SEND =================
def send_message(chat_id, text):
    try:
        requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        }, timeout=10)
    except:
        pass

# ================= TELEGRAM WEBHOOK =================
@app.route("/telegram_webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return "ok"

    # START
    if text.lower() in ["#pay", "/pay"]:
        user_state[chat_id] = "WAIT_AMOUNT"
        send_message(chat_id, "💰 Enter amount ")
        return "ok"

    # AMOUNT INPUT
    if user_state.get(chat_id) == "WAIT_AMOUNT":

        if not text.replace(".", "", 1).isdigit():
            send_message(chat_id, "❌ Invalid amount")
            return "ok"

        amount = float(text)

        if amount <= 0:
            send_message(chat_id, "❌ Amount must be > 0")
            return "ok"

        order_sn = f"ORD_{chat_id}_{int(time.time())}"

        try:
            response = create_payin(order_sn, amount)

            if response.get("status") == 1:

                pay_url = response["data"]["pay_url"]

                orders[order_sn] = {
                    "chat_id": chat_id,
                    "amount": amount,
                    "status": "PENDING"
                }

                send_message(
                    chat_id,
                    f"💳 Payment Link:\n{pay_url}\n\n⏳ Waiting for payment..."
                )

            else:
                send_message(chat_id, f"❌ All trade_type failed:\n{response.get('msg')}")

        except Exception as e:
            print("ERROR:", e)
            send_message(chat_id, "⚠️ Server error")

        user_state.pop(chat_id, None)
        return "ok"

    return "ok"

# ================= AUTO PAY-IN =================
def create_payin(order_sn, amount):
    url = "https://www.lg-pay.com/api/order/create"

    for trade in TRADE_TYPES:

        payload = {
            "app_id": APP_ID,
            "trade_type": trade,
            "order_sn": order_sn,
            "money": int(amount * 100),
            "notify_url": CALLBACK_URL,
            "remark": "telegram_user"
        }

        payload["sign"] = generate_sign(payload, SECRET_KEY)

        try:
            res = requests.post(url, data=payload, timeout=15).json()

            print("TRY:", trade, res)

            if res.get("status") == 1:
                print("SUCCESS TRADE TYPE:", trade)
                return res

        except Exception as e:
            print("ERROR TRY:", trade, e)

    return {"status": 0, "msg": "No valid trade_type found"}

# ================= CALLBACK =================
@app.route("/lgpay_callback", methods=["POST"])
def lgpay_callback():
    data = request.form.to_dict()

    received_sign = data.pop("sign", None)
    calculated_sign = generate_sign(data, SECRET_KEY)

    if received_sign == calculated_sign:

        order_sn = data.get("order_sn")

        if order_sn in orders:
            chat_id = orders[order_sn]["chat_id"]

            send_message(chat_id, "✅ Payment Successful 🎉")

            orders[order_sn]["status"] = "SUCCESS"

        print("CALLBACK OK:", order_sn)
        return "ok"

    else:
        print("INVALID CALLBACK")
        return "invalid"

# ================= HEALTH =================
@app.route("/")
def home():
    return jsonify({"status": "running"})

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
