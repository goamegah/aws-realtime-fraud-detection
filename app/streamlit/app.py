"""
Real-Time Credit Card Fraud Detection Dashboard
================================================
Reads from the ``fraud_predictions`` PostgreSQL table populated by the
streaming pipeline (Kinesis -> Spark/Glue -> RDS) and renders a focused,
operator-grade monitoring UI.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("fraudit.dashboard")

st.set_page_config(
    page_title="Fraud Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "Real-time credit card fraud monitoring.\n\n"
            "Kinesis → Spark/Glue → PostgreSQL → Streamlit."
        )
    },
)


# Design tokens ---------------------------------------------------------------
COLOR_FRAUD = "#ef4444"
COLOR_LEGIT = "#3b82f6"
COLOR_MUTED = "#94a3b8"
COLOR_OK = "#10b981"
COLOR_WARN = "#f59e0b"
PLOTLY_TEMPLATE = "plotly_white"

HIGH_RISK_PROBA = 0.80
CRITICAL_LOOKBACK = timedelta(minutes=15)
DATA_FRESH_S = 60       # < 1 min  -> live
DATA_STALE_S = 600      # < 10 min -> stale


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    name: str
    user: str
    password: str

    @property
    def url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @classmethod
    def from_env(cls) -> "DBConfig":
        def pick(*names: str, default: Optional[str] = None) -> Optional[str]:
            for n in names:
                v = os.getenv(n)
                if v:
                    return v
            return default

        host = pick("DB_HOST", "POSTGRES_HOST")
        name = pick("DB_NAME", "POSTGRES_DB")
        user = pick("DB_USER", "POSTGRES_USER")
        password = pick("DB_PASSWORD", "POSTGRES_PASSWORD")

        missing = [
            label for label, value in (
                ("DB_HOST/POSTGRES_HOST", host),
                ("DB_NAME/POSTGRES_DB", name),
                ("DB_USER/POSTGRES_USER", user),
                ("DB_PASSWORD/POSTGRES_PASSWORD", password),
            ) if not value
        ]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        return cls(
            host=host,                                          # type: ignore[arg-type]
            port=int(pick("DB_PORT", "POSTGRES_PORT", default="5432") or "5432"),
            name=name,                                          # type: ignore[arg-type]
            user=user,                                          # type: ignore[arg-type]
            password=password,                                  # type: ignore[arg-type]
        )


@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    cfg = DBConfig.from_env()
    return create_engine(cfg.url, pool_pre_ping=True, pool_recycle=300)


@st.cache_data(ttl=10, show_spinner=False)
def load_predictions(limit: int = 5000) -> pd.DataFrame:
    query = text(
        """
        SELECT timestamp, user_id, source, fraud_prediction, fraud_proba,
               anomaly_score, ip_address, device_type, os_version, app_version,
               country, region, city, latitude, longitude, processed_at
        FROM fraud_predictions
        ORDER BY processed_at DESC
        LIMIT :limit
        """
    )
    with get_engine().connect() as conn:
        df = pd.read_sql(query, conn, params={"limit": limit})

    if df.empty:
        return df

    for col in ("timestamp", "processed_at"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
        if getattr(df[col].dt, "tz", None) is not None:
            df[col] = df[col].dt.tz_convert("UTC").dt.tz_localize(None)

    df["fraud_prediction"] = df["fraud_prediction"].fillna(0).astype(int)
    df["is_fraud"] = df["fraud_prediction"].astype(bool)
    df["fraud_proba"] = pd.to_numeric(df["fraud_proba"], errors="coerce")
    df["anomaly_score"] = pd.to_numeric(df["anomaly_score"], errors="coerce")
    for c in ("country", "region", "city", "source", "device_type"):
        if c in df.columns:
            df[c] = df[c].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    return df


def latency_seconds(df: pd.DataFrame) -> Optional[float]:
    if df.empty or df["processed_at"].isna().all():
        return None
    last = df["processed_at"].max()
    if pd.isna(last):
        return None
    last_dt = last.to_pydatetime()
    if last_dt.tzinfo is not None:
        last_dt = last_dt.astimezone(timezone.utc).replace(tzinfo=None)
    return max(0.0, (_utcnow().replace(tzinfo=None) - last_dt).total_seconds())


# ---------------------------------------------------------------------------
# Styling — clean, minimal
# ---------------------------------------------------------------------------

CSS = """
<style>
:root {
    --border: rgba(15, 23, 42, 0.08);
    --muted: #64748b;
    --bg-soft: rgba(15, 23, 42, 0.025);
}
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2.5rem;
    max-width: 1400px;
}
section[data-testid="stSidebar"] { border-right: 1px solid var(--border); }

/* Header */
.fmh {
    display: flex; align-items: center; justify-content: space-between;
    padding-bottom: 1rem; margin-bottom: 1rem;
    border-bottom: 1px solid var(--border);
}
.fmh h1 {
    font-size: 1.45rem; font-weight: 700; margin: 0;
    letter-spacing: -0.02em; line-height: 1.2;
}
.fmh .sub { color: var(--muted); font-size: 0.85rem; margin-top: 0.15rem; }

/* Status pill */
.pill {
    display: inline-flex; align-items: center; gap: 0.45rem;
    padding: 0.35rem 0.75rem; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.01em;
    border: 1px solid transparent;
}
.pill .dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.pill.live  { color: #047857; background: rgba(16,185,129,0.10); border-color: rgba(16,185,129,0.25); }
.pill.live .dot { box-shadow: 0 0 0 0 rgba(16,185,129,0.6); animation: pulse 2s infinite; }
.pill.stale { color: #b45309; background: rgba(245,158,11,0.10); border-color: rgba(245,158,11,0.25); }
.pill.off   { color: #b91c1c; background: rgba(239,68,68,0.10); border-color: rgba(239,68,68,0.25); }
@keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(16,185,129,0.6); }
    70%  { box-shadow: 0 0 0 7px rgba(16,185,129,0); }
    100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); }
}

/* KPI cards */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.95rem 1.05rem;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted);
}
[data-testid="stMetricValue"] {
    font-size: 1.75rem !important; font-weight: 700; letter-spacing: -0.02em;
}

/* Section title */
.section {
    font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--muted);
    margin: 1.6rem 0 0.6rem 0;
}

/* Alert banner */
.alert-bar {
    display: flex; align-items: center; gap: 0.75rem;
    padding: 0.75rem 1rem; border-radius: 10px;
    background: rgba(239,68,68,0.06);
    border: 1px solid rgba(239,68,68,0.25);
    color: #991b1b; font-size: 0.9rem; margin-bottom: 0.5rem;
}
.alert-bar strong { color: #7f1d1d; }
.alert-bar .badge {
    background: #b91c1c; color: white; padding: 0.15rem 0.55rem;
    border-radius: 999px; font-size: 0.72rem; font-weight: 700;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0; border-bottom: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    height: 38px; padding: 0 1rem;
    font-size: 0.88rem; font-weight: 500;
}
.stTabs [aria-selected="true"] { font-weight: 600; }

/* Footer */
.fmf {
    margin-top: 2rem; padding-top: 1rem;
    border-top: 1px solid var(--border);
    color: var(--muted); font-size: 0.75rem; text-align: center;
}

/* Hide default streamlit chrome we don't need */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

h3 { font-size: 1rem !important; font-weight: 600 !important; margin-top: 0 !important; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Header & status
# ---------------------------------------------------------------------------

def _status_pill(df: pd.DataFrame) -> str:
    lat = latency_seconds(df)
    if lat is None:
        return '<span class="pill off"><span class="dot"></span>No data</span>'
    if lat < DATA_FRESH_S:
        return f'<span class="pill live"><span class="dot"></span>Live · {lat:.0f}s ago</span>'
    if lat < DATA_STALE_S:
        return f'<span class="pill stale"><span class="dot"></span>{lat/60:.1f} min ago</span>'
    return f'<span class="pill off"><span class="dot"></span>Stale · {lat/60:.0f} min</span>'


def render_header(df: pd.DataFrame) -> None:
    st.markdown(
        f"""
        <div class="fmh">
            <div>
                <h1>🛡️ Fraud Monitor</h1>
                <div class="sub">Real-time credit-card fraud detection · Kinesis → Spark → PostgreSQL</div>
            </div>
            <div>{_status_pill(df)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

@dataclass
class Filters:
    countries: list
    sources: list
    device_types: list
    date_range: Optional[tuple]
    fraud_only: bool
    proba_threshold: float


def _date_window_from_preset(preset: str, max_ts) -> Optional[tuple]:
    offsets = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }
    if preset == "All":
        return None
    if preset in offsets:
        start = (max_ts - offsets[preset]).date()
        return (start, max_ts.date())
    return None


def render_sidebar(df: pd.DataFrame) -> Filters:
    with st.sidebar:
        st.markdown("### ⚙️ Settings")

        with st.expander("Refresh", expanded=True):
            auto = st.toggle("Auto-refresh", value=True)
            interval = st.slider("Interval (s)", 5, 60, 10, 5, disabled=not auto)
            if auto:
                st_autorefresh(interval=interval * 1000, key="data_refresh")
            if st.button("Refresh now", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        if df.empty:
            return Filters([], [], [], None, False, 0.0)

        st.markdown("### 🎛️ Filters")

        max_ts = df["timestamp"].max()
        preset = st.segmented_control(
            "Window",
            options=["1h", "6h", "24h", "7d", "All"],
            default="24h",
        ) if hasattr(st, "segmented_control") else st.radio(
            "Window", ["1h", "6h", "24h", "7d", "All"], horizontal=True, index=2,
        )
        date_range = _date_window_from_preset(preset, max_ts)

        countries_all = sorted(df["country"].dropna().unique().tolist())
        sources_all = sorted(df["source"].dropna().unique().tolist())
        devices_all = sorted(df["device_type"].dropna().unique().tolist())

        countries = st.multiselect("Countries", countries_all, default=countries_all)
        sources = st.multiselect("Sources", sources_all, default=sources_all)
        device_types = st.multiselect("Devices", devices_all, default=devices_all)

        st.markdown("---")
        proba_threshold = st.slider("Min fraud probability", 0.0, 1.0, 0.0, 0.05)
        fraud_only = st.checkbox("Flagged frauds only", value=False)

        st.caption(
            f"**{len(df):,} rows** in cache · last event "
            f"{max_ts:%Y-%m-%d %H:%M} UTC"
        )

        return Filters(
            countries=countries, sources=sources, device_types=device_types,
            date_range=date_range, fraud_only=fraud_only,
            proba_threshold=proba_threshold,
        )


def apply_filters(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    if df.empty:
        return df
    out = df
    if f.countries:    out = out[out["country"].isin(f.countries)]
    if f.sources:      out = out[out["source"].isin(f.sources)]
    if f.device_types: out = out[out["device_type"].isin(f.device_types)]
    if f.fraud_only:   out = out[out["is_fraud"]]
    if f.proba_threshold > 0:
        out = out[out["fraud_proba"].fillna(0) >= f.proba_threshold]
    if f.date_range and len(f.date_range) == 2:
        start, end = f.date_range
        out = out[out["timestamp"].dt.date.between(start, end)]
    return out


# ---------------------------------------------------------------------------
# KPIs & alerts
# ---------------------------------------------------------------------------

def render_kpis(df: pd.DataFrame, df_full: pd.DataFrame) -> None:
    total = len(df)
    frauds = int(df["is_fraud"].sum()) if total else 0
    rate = (frauds / total * 100) if total else 0.0
    avg_proba = df["fraud_proba"].mean() * 100 if total else 0.0

    delta_rate = None
    if total and not df_full.empty:
        now = df_full["timestamp"].max()
        last = df_full[df_full["timestamp"] >= now - timedelta(hours=1)]
        prev = df_full[
            (df_full["timestamp"] >= now - timedelta(hours=2))
            & (df_full["timestamp"] < now - timedelta(hours=1))
        ]
        if len(last) and len(prev):
            delta_rate = last["is_fraud"].mean() * 100 - prev["is_fraud"].mean() * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transactions", f"{total:,}")
    c2.metric("Flagged frauds", f"{frauds:,}")
    c3.metric(
        "Fraud rate", f"{rate:.2f}%",
        delta=f"{delta_rate:+.2f} pp" if delta_rate is not None else None,
        delta_color="inverse",
    )
    c4.metric("Avg. fraud probability", f"{avg_proba:.1f}%")


def render_alert_bar(df: pd.DataFrame) -> int:
    if df.empty or df["processed_at"].isna().all():
        return 0
    ref = df["processed_at"].max()
    recent = df[df["processed_at"] >= ref - CRITICAL_LOOKBACK]
    crit = recent[(recent["is_fraud"]) & (recent["fraud_proba"] >= HIGH_RISK_PROBA)]
    if crit.empty:
        return 0

    top = crit.sort_values("fraud_proba", ascending=False).iloc[0]
    minutes = int(CRITICAL_LOOKBACK.total_seconds() // 60)
    st.markdown(
        f"""
        <div class="alert-bar">
            <span class="badge">{len(crit)}</span>
            <div>
                <strong>High-risk transactions in the last {minutes} min</strong> ·
                top alert: user <code>{top['user_id']}</code> from
                {top.get('city', 'n/a')}, {top.get('country', 'n/a')}
                ({top['fraud_proba']:.0%}).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return len(crit)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _bucket(span_seconds: float) -> str:
    if span_seconds < 3600 * 3:  return "1min"
    if span_seconds < 3600 * 24: return "5min"
    if span_seconds < 3600 * 24 * 7: return "1h"
    return "1d"


def chart_volume(df: pd.DataFrame) -> go.Figure:
    span = (df["timestamp"].max() - df["timestamp"].min()).total_seconds() or 0
    freq = _bucket(span)
    agg = (
        df.groupby(pd.Grouper(key="timestamp", freq=freq))
        .agg(total=("user_id", "count"), frauds=("is_fraud", "sum"))
        .reset_index()
    )
    agg["legit"] = agg["total"] - agg["frauds"]

    fig = go.Figure()
    fig.add_bar(x=agg["timestamp"], y=agg["legit"], name="Legitimate",
                marker_color=COLOR_LEGIT, opacity=0.85)
    fig.add_bar(x=agg["timestamp"], y=agg["frauds"], name="Fraud",
                marker_color=COLOR_FRAUD)
    fig.update_layout(
        barmode="stack", template=PLOTLY_TEMPLATE,
        margin=dict(l=10, r=10, t=10, b=10), height=300,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis_title=None, yaxis_title=None, hovermode="x unified",
    )
    return fig


def chart_geo(df: pd.DataFrame) -> Optional[go.Figure]:
    geo = df.dropna(subset=["latitude", "longitude"])
    if geo.empty:
        return None
    agg = (
        geo.groupby(["latitude", "longitude", "country", "city"])
        .agg(total=("user_id", "count"), frauds=("is_fraud", "sum"))
        .reset_index()
    )
    agg["fraud_rate"] = (agg["frauds"] / agg["total"] * 100).round(2)
    fig = px.scatter_geo(
        agg, lat="latitude", lon="longitude",
        size="total", color="fraud_rate",
        color_continuous_scale=["#3b82f6", "#facc15", "#ef4444"],
        range_color=[0, max(10, float(agg["fraud_rate"].max()))],
        hover_name="city",
        hover_data={
            "country": True, "total": True, "frauds": True, "fraud_rate": ":.2f",
            "latitude": False, "longitude": False,
        },
        size_max=32, projection="natural earth", template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0), height=360,
        coloraxis_colorbar=dict(title="Fraud %", thickness=10, len=0.6),
        geo=dict(showcountries=True, countrycolor="rgba(0,0,0,0.08)",
                 showland=True, landcolor="rgba(15,23,42,0.02)"),
    )
    return fig


def chart_breakdown(df: pd.DataFrame, dim: str) -> go.Figure:
    agg = (
        df.groupby(dim)
        .agg(total=("user_id", "count"), frauds=("is_fraud", "sum"))
        .reset_index()
    )
    agg["fraud_rate"] = (agg["frauds"] / agg["total"] * 100).round(1)
    agg = agg.sort_values("total", ascending=True).tail(8)

    fig = go.Figure()
    fig.add_bar(
        y=agg[dim], x=agg["total"] - agg["frauds"], name="Legit",
        orientation="h", marker_color=COLOR_LEGIT, opacity=0.8,
    )
    fig.add_bar(
        y=agg[dim], x=agg["frauds"], name="Fraud",
        orientation="h", marker_color=COLOR_FRAUD,
        text=[f"{r:.0f}%" for r in agg["fraud_rate"]], textposition="outside",
        textfont=dict(size=11, color=COLOR_MUTED),
    )
    fig.update_layout(
        barmode="stack", template=PLOTLY_TEMPLATE, showlegend=False,
        margin=dict(l=10, r=40, t=10, b=10), height=240,
        xaxis_title=None, yaxis_title=None,
    )
    return fig


def chart_proba_hist(df: pd.DataFrame) -> go.Figure:
    fig = px.histogram(
        df, x="fraud_proba", color="is_fraud", nbins=40,
        color_discrete_map={True: COLOR_FRAUD, False: COLOR_LEGIT},
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10), height=260, bargap=0.02,
        showlegend=False, xaxis_title="Fraud probability", yaxis_title=None,
    )
    return fig


def chart_score_scatter(df: pd.DataFrame) -> go.Figure:
    sample = df.sample(min(len(df), 2500), random_state=42)
    fig = px.scatter(
        sample, x="anomaly_score", y="fraud_proba", color="is_fraud",
        color_discrete_map={True: COLOR_FRAUD, False: COLOR_LEGIT},
        opacity=0.55, template=PLOTLY_TEMPLATE,
        hover_data=["user_id", "country", "source"],
    )
    fig.update_traces(marker=dict(size=6, line=dict(width=0)))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10), height=320, showlegend=False,
        xaxis_title="Anomaly score (RCF)", yaxis_title="Fraud probability (XGB)",
    )
    return fig


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

_TABLE_CFG = {
    "Flag": st.column_config.NumberColumn("Flag", help="1 = fraud, 0 = legit", format="%d"),
    "Proba": st.column_config.ProgressColumn(
        "Proba", help="Fraud probability", min_value=0.0, max_value=1.0, format="%.3f",
    ),
    "Anomaly": st.column_config.NumberColumn("Anomaly", format="%.4f"),
}


def _format_tx(df: pd.DataFrame) -> pd.DataFrame:
    view = df.copy()
    view["fraud_proba"] = view["fraud_proba"].round(4)
    view["anomaly_score"] = view["anomaly_score"].round(4)
    cols = [
        "processed_at", "user_id", "source", "country", "city",
        "device_type", "fraud_prediction", "fraud_proba", "anomaly_score",
    ]
    return view[cols].rename(columns={
        "processed_at": "Time",
        "user_id": "User",
        "source": "Source",
        "country": "Country",
        "city": "City",
        "device_type": "Device",
        "fraud_prediction": "Flag",
        "fraud_proba": "Proba",
        "anomaly_score": "Anomaly",
    })


def render_alerts_table(df: pd.DataFrame) -> None:
    alerts = df[
        (df["is_fraud"]) | (df["fraud_proba"].fillna(0) >= HIGH_RISK_PROBA)
    ].sort_values(["fraud_proba", "processed_at"], ascending=[False, False])

    if alerts.empty:
        st.success("No active alerts in the current window.", icon="✅")
        return

    st.caption(
        f"{len(alerts):,} alert(s) · flagged frauds or fraud probability ≥ "
        f"{HIGH_RISK_PROBA:.0%}."
    )
    st.dataframe(
        _format_tx(alerts.head(200)),
        use_container_width=True, hide_index=True, height=520,
        column_config=_TABLE_CFG,
    )


def render_top_users(df: pd.DataFrame) -> None:
    agg = (
        df.groupby("user_id")
        .agg(
            tx=("user_id", "count"),
            frauds=("is_fraud", "sum"),
            avg_proba=("fraud_proba", "mean"),
            max_anomaly=("anomaly_score", "max"),
            countries=("country", lambda s: ", ".join(sorted(set(s.dropna()))[:3])),
        )
        .reset_index()
    )
    agg = agg[agg["tx"] >= 2].sort_values(
        ["frauds", "avg_proba"], ascending=[False, False]
    ).head(10)

    if agg.empty:
        st.caption("Not enough multi-event users for a ranking.")
        return

    st.dataframe(
        agg.rename(columns={
            "user_id": "User", "tx": "Tx", "frauds": "Frauds",
            "avg_proba": "Avg. proba", "max_anomaly": "Max anomaly",
            "countries": "Countries",
        }),
        use_container_width=True, hide_index=True, height=360,
        column_config={
            "Avg. proba": st.column_config.ProgressColumn(
                "Avg. proba", min_value=0.0, max_value=1.0, format="%.3f",
            ),
            "Max anomaly": st.column_config.NumberColumn("Max anomaly", format="%.4f"),
        },
    )


def render_explorer(df: pd.DataFrame) -> None:
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input("Search user, country, city or IP", "",
                          placeholder="e.g. u_123, Paris, FR, 203.0.113…")
    with c2:
        page_size = st.selectbox("Rows", [50, 100, 200, 500], index=1)

    view = df
    if q:
        s = q.lower()
        mask = pd.Series(False, index=view.index)
        for col in ("user_id", "country", "city", "ip_address"):
            if col in view.columns:
                mask = mask | view[col].astype(str).str.lower().str.contains(s, na=False)
        view = view[mask]

    view = view.sort_values("processed_at", ascending=False).head(page_size)

    if view.empty:
        st.info("No transactions match this search.")
        return

    st.dataframe(
        _format_tx(view),
        use_container_width=True, hide_index=True, height=520,
        column_config=_TABLE_CFG,
    )

    csv = _format_tx(view).to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️  Export current view (CSV)", data=csv,
        file_name=f"fraud_predictions_{_utcnow():%Y%m%d_%H%M%S}.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def render_overview(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No transactions match the current filters.")
        return

    # ── Row 1 — Volume + Geo ────────────────────────────────────────────────
    left, right = st.columns([3, 2])
    with left:
        st.markdown('<div class="section">Volume over time</div>', unsafe_allow_html=True)
        st.plotly_chart(chart_volume(df), use_container_width=True,
                        config={"displayModeBar": False})
    with right:
        st.markdown('<div class="section">Geographic activity</div>', unsafe_allow_html=True)
        fig_geo = chart_geo(df)
        if fig_geo is None:
            st.caption("No geolocated transactions.")
        else:
            st.plotly_chart(fig_geo, use_container_width=True,
                            config={"displayModeBar": False})

    # ── Row 2 — Breakdowns ──────────────────────────────────────────────────
    st.markdown('<div class="section">Where fraud comes from</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("Top countries")
        st.plotly_chart(chart_breakdown(df, "country"), use_container_width=True,
                        config={"displayModeBar": False})
    with c2:
        st.caption("Sources")
        st.plotly_chart(chart_breakdown(df, "source"), use_container_width=True,
                        config={"displayModeBar": False})
    with c3:
        st.caption("Devices")
        st.plotly_chart(chart_breakdown(df, "device_type"), use_container_width=True,
                        config={"displayModeBar": False})

    # ── Row 3 — Model insights + Top users ──────────────────────────────────
    st.markdown('<div class="section">Model insights</div>', unsafe_allow_html=True)
    a, b = st.columns([2, 3])
    with a:
        st.caption("Fraud probability distribution (XGBoost)")
        st.plotly_chart(chart_proba_hist(df), use_container_width=True,
                        config={"displayModeBar": False})
        st.caption("Top users at risk")
        render_top_users(df)
    with b:
        st.caption("Anomaly score (RCF) vs. fraud probability (XGB)")
        st.plotly_chart(chart_score_scatter(df), use_container_width=True,
                        config={"displayModeBar": False})


def main() -> None:
    try:
        df_full = load_predictions(limit=5000)
    except Exception as exc:
        st.error("Unable to connect to the database.", icon="🚫")
        with st.expander("Error details"):
            st.code(str(exc))
        st.stop()

    render_header(df_full)

    if df_full.empty:
        st.warning(
            "No predictions in `fraud_predictions`. Make sure the streaming "
            "pipeline (Kinesis → Spark → RDS) is running and the data generator "
            "is producing transactions.",
            icon="⏳",
        )
        st.stop()

    filters = render_sidebar(df_full)
    df = apply_filters(df_full, filters)

    n_alerts = render_alert_bar(df)
    render_kpis(df, df_full)

    overview_tab, alerts_tab, explorer_tab = st.tabs([
        "Overview",
        f"🚨 Alerts" + (f" · {n_alerts}" if n_alerts else ""),
        "🔍 Explorer",
    ])

    with overview_tab:
        render_overview(df)
    with alerts_tab:
        render_alerts_table(df)
    with explorer_tab:
        render_explorer(df)

    st.markdown(
        f"""
        <div class="fmf">
            Updated {_utcnow():%Y-%m-%d %H:%M:%S} UTC ·
            Kinesis → Spark/Glue → PostgreSQL ·
            SageMaker XGBoost + Random Cut Forest
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
