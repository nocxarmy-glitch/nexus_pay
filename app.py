import requests
import hashlib
import time
from flask import Flask, request

app = Flask(__name__)

# ================= CONFIG =================
APP_ID = "YD5038"
SECRET_KEY = "WdX2XVTDnV8dmpc2GMl4EaDW9lMH2DTT"
TELEGRAM_BOT_TOKEN = "8660649540:AAECvvBwKYk8vz6DXQSA82CNRe1dupqMnj4"

BASE_URL = "https://nexus-pay.onrender.com"
CALLBACK_URL = f"{BASE_URL}/lgpay_callback"

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ================= USER STATE =================
user_state = {}
orders = {}

# ================= SIGN =================
def generate_sign(data, key):
    data = {k: v for k, v in data.items() if v != "" and v is not None}
    sorted_data = dict(sorted(data.items()))
    stringA = "&".join([f"{k}={v}" for k, v in sorted_data.items()])
    stringA = f"{stringA}&key={key}"
    return hashlib.md5(stringA.encode()).hexdigest().upper()

# ================= TELEGRAM =================
def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# ================= WEBHOOK =================
@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    message = data.get("message", {})

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return "ok"

    # START
    if text.lower() == "/pay":
        user_state[chat_id] = "WAIT_AMOUNT"
        send_message(chat_id, "💰 Enter amount (example: 2000)")
        return "ok"

    # ENTER AMOUNT
    if user_state.get(chat_id) == "WAIT_AMOUNT":

        if not text.replace(".", "", 1).isdigit():
            send_message(chat_id, "❌ Invalid amount")
            return "ok"

        amount = float(text)

        if amount <= 0:
            send_message(chat_id, "❌ Amount must be > 0")
            return "ok"

        order_sn = f"PAYIN_{chat_id}_{int(time.time())}"

        try:
            res = create_payin(order_sn, amount)

            if res.get("status") == 1:
                pay_url = res["data"]["pay_url"]

                orders[order_sn] = {
                    "chat_id": chat_id,
                    "amount": amount,
                    "status": "PENDING"
                }

                send_message(chat_id, f"💳 Pay here:\n{pay_url}")

            else:
                send_message(chat_id, f"❌ Failed: {res.get('msg')}")

        except Exception as e:
            print("ERROR:", e)
            send_message(chat_id, "⚠️ Server error")

        user_state.pop(chat_id, None)
        return "ok"

    return "ok"

# ================= CREATE PAY-IN =================
def create_payin(order_sn, amount):
    url = "https://www.lg-pay.com/api/order/create"

    data = {
        "app_id": APP_ID,
        "trade_type": "test",  # ⚠️ change to real later
        "order_sn": order_sn,
        "money": int(amount * 100),
        "notify_url": CALLBACK_URL,
        "remark": "telegram"
    }

    data["sign"] = generate_sign(data, SECRET_KEY)

    res = requests.post(url, data=data, timeout=15)
    return res.json()

# ================= CALLBACK =================
@app.route('/lgpay_callback', methods=['POST'])
def lgpay_callback():
    data = request.form.to_dict()

    received_sign = data.pop("sign", None)
    calculated_sign = generate_sign(data, SECRET_KEY)

    if received_sign == calculated_sign:

        order_sn = data.get("order_sn")

        if order_sn in orders:
            chat_id = orders[order_sn]["chat_id"]

            send_message(chat_id, "✅ Payment Successful")

            orders[order_sn]["status"] = "SUCCESS"

        print("✅ CALLBACK VERIFIED:", order_sn)
        return "ok"

    else:
        print("❌ INVALID SIGN")
        return "invalid"

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
