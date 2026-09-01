import streamlit as st
import json
import pandas as pd
from batch_simulator import run_batch

st.set_page_config(page_title="SmartRecover AI Dashboard", layout="wide")
st.title("SmartRecover AI — Autonomous Revenue Recovery")

# Control Panel in Sidebar
st.sidebar.header("Batch Controls")
if st.sidebar.button("▶ Run 50-Record Batch Simulation"):
    with st.spinner("Processing 50 transactions with Gemini & Razorpay guardrails..."):
        run_batch(50)
    st.sidebar.success("Batch simulation complete!")
    st.rerun()

# Load Audit Logs
try:
    with open("audit_log.json", "r") as f:
        logs = json.load(f)
except Exception:
    logs = []

if not logs:
    st.warning("No audit log found. Click **'▶ Run 50-Record Batch Simulation'** in the left sidebar to generate live recovery data.")
else:
    total_tx = len(logs)
    total_amount = sum(item["amount"] for item in logs)
    recovered_amount = sum(item["amount"] for item in logs if item.get("recovered"))
    recovery_rate = (recovered_amount / total_amount * 100) if total_amount > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Failed Tx", total_tx)
    col2.metric("Total Value at Risk", f"INR {total_amount:,.2f}")
    col3.metric("Estimated Recovered", f"INR {recovered_amount:,.2f}")
    col4.metric("Recovery Rate", f"{recovery_rate:.1f}%")

    st.markdown("---")
    st.subheader("Live Agent Audit Ledger")
    
    table_data = []
    for item in logs:
        table_data.append({
            "Payment ID": item["payment_id"],
            "Amount (INR)": item["amount"],
            "Error Code": item["error_code"],
            "Diagnosis": item["decision"]["failure_type"],
            "Recovery Action": item["decision"]["action_type"],
            "Reasoning": item["decision"]["reasoning"],
            "Execution Output": str(item["execution"])
        })
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)