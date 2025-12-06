
import os
import hmac
import hashlib
import json
import sqlite3
from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH")
WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")


app = Flask(__name__)


def update_payment_and_order_by_internal_order(internal_order_id: int, new_status: str):
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    
    cur.execute("UPDATE payments SET status = ? WHERE order_id = ?", (new_status, internal_order_id))

    
    if new_status.lower() in ("success", "captured", "paid"):
        cur.execute(
            "UPDATE orders SET payment_status = ?, payment_mode = ?, status = 'paid' WHERE order_id = ?",
            (new_status, "Online", internal_order_id)
        )
    else:
        cur.execute(
            "UPDATE orders SET payment_status = ? WHERE order_id = ?",
            (new_status, internal_order_id)
        )

    conn.commit()
    conn.close()


@app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    
    raw_body = request.get_data(as_text=True)
    signature = request.headers.get("X-Razorpay-Signature")

    if signature is None:
        abort(400, "Missing signature header")

    #verify signature
    generated_signature = hmac.new(
        key=WEBHOOK_SECRET.encode("utf-8"),
        msg=raw_body.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(generated_signature, signature):
        abort(400, "Invalid signature")

    # 3)  payload
    payload = request.json or {}
    event = payload.get("event", "").lower()

    #  extract internal_order_id from  payload 
    internal_order_id = None
    try:
       
        
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {}) or {}
        pl_entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {}) or {}

        notes = payment_entity.get("notes", {}) or pl_entity.get("notes", {})
        if notes and notes.get("internal_order_id"):
            internal_order_id = int(notes.get("internal_order_id"))
    except Exception:
        internal_order_id = None

    if internal_order_id is None:
        
        try:
            
            for k in ("payment", "payment_link", "order"):
                ent = payload.get("payload", {}).get(k, {}).get("entity", {}) or {}
                if ent.get("notes", {}) and ent["notes"].get("internal_order_id"):
                    internal_order_id = int(ent["notes"]["internal_order_id"])
                    break
        except Exception:
            internal_order_id = None

    if internal_order_id is None:
       
        
        print("internal_order_id not found in payload. payload:", json.dumps(payload)[:1000])
        abort(400, "internal_order_id not found in payload")

    # payment status
    mapped_status = "unknown"
    
    if event.endswith("payment.captured") or event == "payment.captured":
        mapped_status = "success"
    elif event.endswith("payment.failed") or event == "payment.failed":
        mapped_status = "failed"
    elif event == "payment_link.paid" or "paid" in event:
        
        mapped_status = "success"
    else:
       
        ent_status = payment_entity.get("status") or pl_entity.get("status")
        if ent_status:
            mapped_status = ent_status

    # DB update
    update_payment_and_order_by_internal_order(internal_order_id, mapped_status)

    # Respond 
    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    
    app.run(host="0.0.0.0", port=5000, debug=True)
