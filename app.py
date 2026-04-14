import requests
import hashlib
from flask import Flask, request

app = Flask(__name__)

# ================= CONFIG =================
APP_ID = "YD5038"
SECRET_KEY = "WdX2XVTDnV8dmpc2GMl4EaDW9lMH2DTT"
TELEGRAM_BOT_TOKEN = "8660649540:AAECvvBwKYk8vz6DXQSA82CNRe1dupqMnj4"

CALLBACK_URL = "https://nexus-pay.onrender.com/lgpay_callback"

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ================= USER STATE =================
user_state = {}

# ================= SIGN FUNCTION (OFFICIAL LOGIC) =================
def generate_sign(data, key):
    data = {k: v for k, v in data.items() if v != "" and v is not None}
    sorted_data = dict(sorted(data.items()))

    stringA = "&".join([f"{k}={v}" for k, v in sorted_data.items()])
    stringA = f"{stringA}&key={key}"

    return hashlib.md5(stringA.encode()).hexdigest().upper()


# ================= TELEGRAM WEBHOOK =================
@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    message = data.get("message", {})

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return "ok"

    # STEP 1
    if text.lower() == "#pay":
        user_state[chat_id] = "WAIT_AMOUNT"
        send_message(chat_id, "💰 Enter amount (example: 5000)")
        return "ok"

    # STEP 2
    if user_state.get(chat_id) == "WAIT_AMOUNT":

        if not text.replace(".", "", 1).isdigit():
            send_message(chat_id, "❌ Invalid amount")
            return "ok"

        amount = float(text)

        if amount <= 0:
            send_message(chat_id, "❌ Amount must be > 0")
            return "ok"

        order_sn = f"ORD_{chat_id}_{message.get('date')}"

        try:
            res = create_payout(order_sn, amount)

            if res.get("status") == 1:
                send_message(chat_id, f"✅ Order Created\n₹{amount}\nStatus: Processing")
            else:
                send_message(chat_id, f"❌ Failed: {res.get('msg')}")

        except Exception as e:
            print("ERROR:", e)
            send_message(chat_id, "⚠️ Server error")

        user_state.pop(chat_id, None)
        return "ok"

    return "ok"


# ================= CREATE PAYOUT =================
def create_payout(order_sn, amount):
    url = "https://www.lg-pay.com/api/deposit/create"

    data = {
        "app_id": APP_ID,
        "order_sn": order_sn,
        "currency": "INR",
        "money": int(amount * 100),
        "notify_url": CALLBACK_URL,

        # 🔥 Your payout details
        "name": "MOHIT GODARA",
        "bank_name": "Federal Bank",
        "addon1": "FDRL0000000",
        "card_number": "99980123036258"
    }

    data["sign"] = generate_sign(data, SECRET_KEY)

    response = requests.post(url, data=data, timeout=15)
    return response.json()


# ================= CALLBACK =================
@app.route('/lgpay_callback', methods=['POST'])
def lgpay_callback():
    data = request.form.to_dict()

    received_sign = data.pop("sign", None)

    calculated_sign = generate_sign(data, SECRET_KEY)

    if received_sign == calculated_sign:
        order_sn = data.get("order_sn")
        status = data.get("status")
        msg = data.get("msg")

        print(f"✅ CALLBACK VERIFIED: {order_sn} | STATUS: {status}")

        return "ok"
    else:
        print("❌ INVALID SIGN")
        return "invalid"


# ================= TELEGRAM SEND =================
def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
