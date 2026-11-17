import random
import time
import os
import requests

# ============================================================
# YOUR FAST2SMS API KEY
# ============================================================
FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY", "qtsmS7pRicHgdGhUNvYIlF10ueXCPk6awO59M2DBf3Anr4TWLzADMlyzFi0HGEdnVeBWu5ZfC6mJhocs")
# ============================================================

FAST2SMS_URL = "https://www.fast2sms.com/dev/bulkV2"

# In-memory OTP store: {phone: {otp, timestamp, attempts}}
otp_store = {}
OTP_EXPIRY = 300  # 5 minutes
MAX_ATTEMPTS = 3

# Master demo OTP — always accepted so live demos never get stuck
# (real SMS OTPs still work too). Set DEMO_OTP=off in .env for production.
DEMO_OTP = os.getenv("DEMO_OTP", "1234")


def generate_otp():
    return str(random.randint(1000, 9999))


def send_otp(phone: str) -> dict:
    """Send OTP via Fast2SMS. Falls back to demo OTP 1234 if no API key."""
    phone = phone.strip().replace("+91", "").replace(" ", "")

    # Demo mode — no API key configured
    if not FAST2SMS_API_KEY or FAST2SMS_API_KEY == "PASTE_YOUR_KEY_HERE":
        otp_store[phone] = {"otp": "1234", "timestamp": time.time(), "attempts": 0}
        print(f"[DEMO MODE] OTP for {phone}: 1234")
        return {"success": True, "message": "Demo OTP sent (1234)", "demo": True}

    otp = generate_otp()

    try:
        response = requests.get(
            FAST2SMS_URL,
            params={
                "authorization": FAST2SMS_API_KEY,
                "route": "otp",
                "variables_values": otp,
                "flash": 0,
                "numbers": phone,
            },
            headers={"cache-control": "no-cache"},
            timeout=10,
        )
        data = response.json()

        if data.get("return"):
            otp_store[phone] = {"otp": otp, "timestamp": time.time(), "attempts": 0}
            print(f"[FAST2SMS] OTP sent to {phone}")
            return {"success": True, "message": "OTP sent successfully"}
        else:
            print(f"[FAST2SMS] Failed: {data}")
            # Fallback to demo
            otp_store[phone] = {"otp": "1234", "timestamp": time.time(), "attempts": 0}
            return {"success": True, "message": f"SMS failed ({data.get('message', 'unknown')}), demo OTP: 1234", "demo": True}

    except Exception as e:
        print(f"[FAST2SMS] Error: {e}")
        otp_store[phone] = {"otp": "1234", "timestamp": time.time(), "attempts": 0}
        return {"success": True, "message": "SMS service error, demo OTP: 1234", "demo": True}


def verify_otp(phone: str, otp: str) -> dict:
    """Verify the OTP entered by user."""
    phone = phone.strip().replace("+91", "").replace(" ", "")

    if DEMO_OTP and DEMO_OTP.lower() != "off" and otp.strip() == DEMO_OTP:
        otp_store.pop(phone, None)
        return {"success": True, "message": "OTP verified"}

    record = otp_store.get(phone)
    if not record:
        return {"success": False, "message": "No OTP sent to this number. Request a new one."}

    # Check expiry
    if time.time() - record["timestamp"] > OTP_EXPIRY:
        del otp_store[phone]
        return {"success": False, "message": "OTP expired. Request a new one."}

    # Check attempts
    if record["attempts"] >= MAX_ATTEMPTS:
        del otp_store[phone]
        return {"success": False, "message": "Too many wrong attempts. Request a new OTP."}

    # Verify
    if record["otp"] == otp.strip():
        del otp_store[phone]
        return {"success": True, "message": "OTP verified"}
    else:
        record["attempts"] += 1
        return {"success": False, "message": f"Wrong OTP. {MAX_ATTEMPTS - record['attempts']} attempts left."}