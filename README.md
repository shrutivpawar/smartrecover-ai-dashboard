# SmartRecover AI — Autonomous Revenue Recovery Agent

An autonomous, bounded payment recovery engine built for the **Razorpay AI Buildathon (Track 03 — AI Revenue Recovery)**.

SmartRecover AI closes the loop from payment failure detection to root-cause diagnosis, safe workflow execution, and auditable financial recovery—recovering lost revenue from soft declines, mandate failures, and user limits without spamming customers or triggering bank throttling.

---

##  Problem Overview

Payment failures in Indian digital commerce (UPI, Netbanking, Cards, e-Mandates) quietly bleed merchant margins:
- **Blind Retries:** Naive scripts re-attempt payments immediately, failing repeatedly and triggering bank rate limits.
- **Generic Reminders:** Customers receive static SMS alerts instead of frictionless 1-click alternative recovery paths.
- **Unbounded Loss:** Lack of policy guardrails causes unmonitored drop-offs and uncontrolled customer churn.

---

##  Key Features

* **Intelligent Root-Cause Diagnosis:** Leverages Gemini Structured Outputs (`Pydantic` schema enforcement) to categorize failures into transient network spikes, fund limits, or expired instruments.
* **Bounded Autonomous Actions:**
  * `GENERATE_PAYMENT_LINK`: Automatically generates dynamic, 1-click Razorpay payment links.
  * `RETRY_DELAYED`: Calculates backoff retry windows for bank server/gateway outages.
  * `REQUEST_NEW_MANDATE`: Triggers recurring mandate re-authentication.
  * `ESCALATE_MANUAL`: Quarantines high-risk or repeatedly failing transactions.
* **Deterministic Guardrails:** Hard-coded safety policies (max 3 retry limit, rate-limit backoff, and signature verification) running outside the LLM.
* **Real-time Streamlit Dashboard:** Live financial ledger tracking total volume at risk, recovery yield, and complete LLM reasoning audit trails.
* **Signature Verification:** Built-in HMAC-SHA256 webhook validator for Razorpay event callbacks.

---

##  Architecture & System Design

```text
+-------------------------------------------------------------+
|               Razorpay Test Mode / Simulated Batch          |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|               FastAPI Ingestion & Webhook Layer             |
|              - Verifies X-Razorpay-Signature (HMAC)         |
|              - Parses payment.failed / subscription error   |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|              SmartRecover AI Autonomous Agent               |
|  ┌───────────────────────────────────────────────────────┐  |
|  | Root-Cause Classification (Gemini 3.6 Flash)          |  |
|  ├───────────────────────────────────────────────────────┤  |
|  | Programmatic Guardrails (Deterministic Policy Layer):  |  |
|  | - Max 3 Retries Capped -> Escalate Manual             |  |
|  | - Exponential Backoff on 503/429 Spikes               |  |
|  └───────────────────────────────────────────────────────┘  |
+-------------------------------------------------------------+
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
+-----------------------+           +-----------------------+
|  Razorpay Test API    |           | Immutable Audit Trail |
|  - Payment Links      |           | (audit_log.json)      |
|  - Mandate Re-auth    |           | - Streamlit Dashboard |
+-----------------------+           +-----------------------+

```

---

##  Complete Project Structure & Files
```

razorpay-smart-recover/
│
├── .env.example            # Template for required environment variables
├── .gitignore              # Ignored files (prevents API key leakage)
├── requirements.txt        # Python package dependencies
├── README.md               # Main repository documentation
│
├── agent.py                # Core LLM diagnosis, guardrails, and Razorpay API execution
├── batch_simulator.py      # Synthetic 50-record payment failure processor
├── dashboard.py            # Streamlit live audit ledger & recovery visualizer
├── app.py                  # FastAPI webhook listener with HMAC signature check
└── audit_log.json          # Persisted JSON ledger generated during runtime
```

---

##  Quickstart & Execution

1. Activate Environment & Install Dependencies
```
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
2. Run the 50-Record Batch Simulation
```
python batch_simulator.py
```
4. Launch the Audit Ledger Dashboard
```
streamlit run dashboard.py
```

---

##  What Broke at 2 AM & The Engineering Fix
* The Problem:
   * Firing rapid batch calls caused transient API rate-limit spikes (503 UNAVAILABLE / 429 Rate Exceeded) and potential double-charging risks on repeated retries.

* The Solution:
   * Implemented a jittered exponential backoff retry wrapper (call_llm_with_retry) with deterministic fallbacks.
   * Enforced strict programmatic bounding outside the LLM: capped transactions at 3 retries max before forcing an ESCALATE_MANUAL status into the audit ledger.


