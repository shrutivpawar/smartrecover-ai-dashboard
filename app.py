import os
import hmac
import hashlib
from fastapi import FastAPI, Request, Header, HTTPException
from agent import run_recovery_agent
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Razorpay SmartRecover Webhook Engine")
WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

def verify_signature(payload_body: bytes, signature: str) -> bool:
    if not WEBHOOK_SECRET:
        return True  # Fallback for local testing if secret not configured
    generated_sig = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_sig, signature)

@app.post("/webhook/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None)
):
    body = await request.body()
    
    if x_razorpay_signature and not verify_signature(body, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid HMAC Signature")

    payload = await request.json()
    event = payload.get("event")

    # Intercept payment failure events
    if event in ["payment.failed", "subscription.charged_failed"]:
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        
        tx_data = {
            "payment_id": payment_entity.get("id", "pay_unknown"),
            "amount": payment_entity.get("amount", 0),
            "error_code": payment_entity.get("error_code", "GENERIC_ERROR"),
            "error_description": payment_entity.get("error_description", "Payment processing failed"),
            "method": payment_entity.get("method", "upi"),
            "customer_email": payment_entity.get("email", "customer@example.com"),
            "retry_count": 0
        }
        
        result = run_recovery_agent(tx_data)
        return {"status": "success", "recovered_action": result["decision"]["action_type"]}

    return {"status": "ignored", "event": event}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "SmartRecover AI"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.py:app", host="0.0.0.0", port=8000, reload=True)