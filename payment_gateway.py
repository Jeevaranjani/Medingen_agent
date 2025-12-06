

import os
from dotenv import load_dotenv
import razorpay

load_dotenv()

KEY_ID = os.getenv("RAZORPAY_KEY_ID")
KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")



client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))


def create_payment_link(total_amount_rupees: float,
                        customer_name: str,
                        customer_phone: str,
                        customer_email: str,
                        internal_order_id: int):
   
    amount_paise = int(round(total_amount_rupees * 100))

    payload = {
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": f"Medingen Order {internal_order_id}",
        "customer": {
            "name": customer_name,
            "contact": customer_phone,
            "email": customer_email
        },
        "notes": {
            "internal_order_id": str(internal_order_id)
        },
        "notify": {
            "sms": True,
            "email": True
        }
    }

    resp = client.payment_link.create(payload)
    
    return {
        "provider_id": resp.get("id"),
        "short_url": resp.get("short_url"),
        "status": resp.get("status")
    }
