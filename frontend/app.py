import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# Chargement des variables d'environnement
load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_PORT = os.getenv("POSTGRES_PORT", 5432)

print("🔍 DEBUG DB HOST:", os.getenv("POSTGRES_HOST"))

# Connexion à la base PostgreSQL
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Rafraîchissement toutes les 10 secondes
st_autorefresh(interval=10 * 1000, key="refresh")

st.set_page_config(layout="wide", page_title="📊 Fraud Detection Dashboard")
st.title("🔍 Real-Time Credit Card Fraud Dashboard")

# Récupération des données
query = "SELECT * FROM fraud_predictions ORDER BY created_at DESC LIMIT 1000;"
df = pd.read_sql(query, engine)

# Transformation
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["created_at"] = pd.to_datetime(df["created_at"])
df["is_fraud"] = df["fraud_prediction"].astype(bool)

# Zone de filtres
with st.sidebar:
    st.header("🎛️ Filtres")
    countries = st.multiselect("🌍 Pays", options=df["country"].unique(), default=list(df["country"].unique()))
    sources = st.multiselect("🛒 Source", options=df["source"].unique(), default=list(df["source"].unique()))
    date_range = st.date_input("📅 Période", [df["timestamp"].min(), df["timestamp"].max()])

# Application des filtres
df = df[df["country"].isin(countries)]
df = df[df["source"].isin(sources)]
df = df[df["timestamp"].dt.date.between(*date_range)]

# KPIs
total_tx = len(df)
total_frauds = df["is_fraud"].sum()
fraud_ratio = (total_frauds / total_tx * 100) if total_tx > 0 else 0
avg_proba = df["fraud_proba"].mean() * 100 if total_tx > 0 else 0

st.markdown("### 📈 Statistiques Générales")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Transactions", total_tx)
col2.metric("Fraudes détectées", total_frauds)
col3.metric("Tx de fraude (%)", f"{fraud_ratio:.2f}%")
col4.metric("Proba fraude moyenne", f"{avg_proba:.2f}%")

# Graphiques temporels
st.markdown("### ⏳ Transactions dans le temps")
time_agg = df.groupby(pd.Grouper(key="timestamp", freq="1min")).agg(fraudes=("is_fraud", "sum"), total=("id", "count")).reset_index()
fig = px.line(time_agg, x="timestamp", y=["fraudes", "total"], labels={"value": "Nombre", "timestamp": "Heure"}, title="Volume de transactions & fraudes")
st.plotly_chart(fig, use_container_width=True)

# Carte
st.markdown("### 🌍 Carte des transactions")
st.map(df[["latitude", "longitude"]])

# Tableau
st.markdown("### 📄 Dernières transactions")
st.dataframe(df[[
    "created_at", "user_id", "source", "country", "device_type",
    "fraud_prediction", "fraud_proba", "anomaly_score"
]].head(50))
