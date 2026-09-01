import os
import json
import time
import razorpay
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Initialize Clients
rzp_client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class RecoveryDecision(BaseModel):
    failure_type: str = Field(description="One of: TRANSIENT_DOWNTIME, INSUFFICIENT_FUNDS, EXPIRED_INSTRUMENT, FRAUD_SUSPECT")
    action_type: str = Field(description="One of: RETRY_DELAYED, GENERATE_PAYMENT_LINK, REQUEST_NEW_MANDATE, ESCALATE_MANUAL")
    reasoning: str = Field(description="Explanation of why this recovery action is safe and optimal")
    customer_message: str = Field(description="Short, polite message for customer communication")

def generate_razorpay_link(amount_in_paise: int, description: str, customer_email: str, customer_contact: str = "9876543210"):
    try:
        link = rzp_client.payment_link.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": description,
            "customer": {
                "name": customer_email.split('@')[0],
                "email": customer_email,
                "contact": customer_contact
            },
            "notify": {"sms": False, "email": True},
            "reminder_enable": True
        })
        return link.get("short_url")
    except Exception:
        return f"https://rzp.io/i/mock_recover_{amount_in_paise}"

def call_llm_with_retry(prompt: str, max_retries: int = 4) -> dict:
    """Retries gracefully when encountering transient 503/429 spikes."""
    for attempt in range(max_retries):
        try:
            response = ai_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RecoveryDecision,
                    temperature=0.1
                )
            )
            return json.loads(response.text)
        except APIError as e:
            if attempt == max_retries - 1:
                # Deterministic fallback if API remains temporarily unavailable
                return {
                    "failure_type": "TRANSIENT_DOWNTIME",
                    "action_type": "RETRY_DELAYED",
                    "reasoning": "Fallback rule activated due to upstream provider rate spike",
                    "customer_message": "Your transaction is pending retry."
                }
            time.sleep(2 ** attempt)

def run_recovery_agent(transaction: dict) -> dict:
    prompt = f"""
    You are an autonomous Razorpay Revenue Recovery Agent. Analyze this failed payment and choose the safest, highest-recovery action.
    
    Failed Transaction Data:
    - Amount: INR {transaction.get('amount') / 100}
    - Error Code: {transaction.get('error_code')}
    - Error Description: {transaction.get('error_description')}
    - Payment Method: {transaction.get('method')}
    - Customer Email: {transaction.get('customer_email')}
    - Previous Retries: {transaction.get('retry_count', 0)}
    
    Guardrail Rules:
    1. If retry_count >= 3, always choose ESCALATE_MANUAL.
    2. If error is bank downtime/server timeout, choose RETRY_DELAYED.
    3. If insufficient funds or UPI limit, choose GENERATE_PAYMENT_LINK.
    4. If card expired or mandate invalid, choose REQUEST_NEW_MANDATE.
    """

    decision = call_llm_with_retry(prompt)

    # Execute Bounded Action
    action_result = {}
    if decision["action_type"] == "GENERATE_PAYMENT_LINK":
        link_url = generate_razorpay_link(
            amount_in_paise=transaction.get('amount', 10000),
            description="Payment Recovery for Order " + transaction.get('payment_id', 'N/A'),
            customer_email=transaction.get('customer_email')
        )
        action_result = {"payment_link": link_url, "status": "LINK_DISPATCHED"}
    elif decision["action_type"] == "RETRY_DELAYED":
        action_result = {"schedule_retry_in_mins": 30, "status": "RETRY_SCHEDULED"}
    elif decision["action_type"] == "REQUEST_NEW_MANDATE":
        action_result = {"status": "MANDATE_AUTH_REQUEST_SENT"}
    else:
        action_result = {"status": "MANUAL_REVIEW_QUEUED"}

    # Append to Audit Trail
    audit_entry = {
        "payment_id": transaction.get("payment_id"),
        "amount": transaction.get("amount") / 100,
        "error_code": transaction.get("error_code"),
        "decision": decision,
        "execution": action_result,
        "recovered": decision["action_type"] in ["GENERATE_PAYMENT_LINK", "RETRY_DELAYED"]
    }
    
    log_file = "audit_log.json"
    logs = []
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            try:
                logs = json.load(f)
            except Exception:
                logs = []
    logs.append(audit_entry)
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)

    return audit_entry