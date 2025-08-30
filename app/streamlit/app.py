import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# Load environment variables
load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_PORT = os.getenv("POSTGRES_PORT", 5432)

print("🔍 DEBUG DB HOST:", os.getenv("POSTGRES_HOST"))

# Connect to PostgreSQL database
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Refresh every 10 seconds
st_autorefresh(interval=10 * 1000, key="refresh")

st.set_page_config(layout="wide", page_title="📊 Fraud Detection Dashboard")
st.title("🔍 Real-Time Credit Card Fraud Dashboard")

# Fetch data
query = "SELECT * FROM fraud_predictions ORDER BY processed_at DESC LIMIT 1000;"
df = pd.read_sql(query, engine)

# Transform data
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["processed_at"] = pd.to_datetime(df["processed_at"])
df["is_fraud"] = df["fraud_prediction"].astype(bool)

# Filter section
with st.sidebar:
    st.header("🎛️ Filters")
    countries = st.multiselect("🌍 Countries", options=df["country"].unique(), default=list(df["country"].unique()))
    sources = st.multiselect("🛒 Source", options=df["source"].unique(), default=list(df["source"].unique()))
    date_range = st.date_input("📅 Time Period", [df["timestamp"].min(), df["timestamp"].max()])

# Apply filters
df = df[df["country"].isin(countries)]
df = df[df["source"].isin(sources)]
df = df[df["timestamp"].dt.date.between(*date_range)]

# KPIs
total_tx = len(df)
total_frauds = df["is_fraud"].sum()
fraud_ratio = (total_frauds / total_tx * 100) if total_tx > 0 else 0
avg_proba = df["fraud_proba"].mean() * 100 if total_tx > 0 else 0

st.markdown("### 📈 General Statistics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Transactions", total_tx)
col2.metric("Detected Frauds", total_frauds)
col3.metric("Fraud Rate (%)", f"{fraud_ratio:.2f}%")
col4.metric("Average Fraud Probability", f"{avg_proba:.2f}%")

# Time series charts
st.markdown("### ⏳ Transactions Over Time")
time_agg = df.groupby(pd.Grouper(key="timestamp", freq="1min")).agg(frauds=("is_fraud", "sum"),
                                                                    total=("user_id", "count")).reset_index()
fig = px.line(time_agg, x="timestamp", y=["frauds", "total"], labels={"value": "Count", "timestamp": "Time"},
              title="Transaction & Fraud Volume")
st.plotly_chart(fig, use_container_width=True)

# Map
st.markdown("### 🌍 Transaction Map")
st.map(df[["latitude", "longitude"]])

# Table
st.markdown("### 📄 Latest Transactions")
st.dataframe(df[[
    "processed_at", "user_id", "source", "country", "device_type",
    "fraud_prediction", "fraud_proba", "anomaly_score"
]].head(50))
