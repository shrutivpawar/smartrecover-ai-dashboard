import json
import random
import time
from agent import run_recovery_agent

error_scenarios = [
    {"code": "BAD_REQUEST_ERROR", "desc": "Bank server downtime / timeout", "method": "upi", "retries": 0},
    {"code": "GATEWAY_ERROR", "desc": "Insufficient balance in customer account", "method": "upi", "retries": 1},
    {"code": "CARD_EXPIRED", "desc": "Card validity period expired", "method": "card", "retries": 0},
    {"code": "LIMIT_EXCEEDED", "desc": "Transaction amount exceeds daily limit", "method": "netbanking", "retries": 0},
    {"code": "RETRY_EXHAUSTED", "desc": "Multiple failed attempts", "method": "upi", "retries": 3}
]

def run_batch(num_records=50):
    print(f"--- Simulating and Processing {num_records} Failed Transactions ---")
    
    with open("audit_log.json", "w") as f:
        json.dump([], f)

    for i in range(1, num_records + 1):
        scenario = random.choice(error_scenarios)
        tx = {
            "payment_id": f"pay_test_{1000 + i}",
            "amount": random.choice([49900, 99900, 149900, 299900, 499900]),
            "error_code": scenario["code"],
            "error_description": scenario["desc"],
            "method": scenario["method"],
            "customer_email": f"customer_{i}@example.com",
            "retry_count": scenario["retries"]
        }
        result = run_recovery_agent(tx)
        print(f"[{i:02d}/{num_records}] {tx['payment_id']} | Action: {result['decision']['action_type']}")
        time.sleep(0.4)  # Prevents API bursts

    print("\nBatch Complete! Launching dashboard...")

if __name__ == "__main__":
    run_batch(50)