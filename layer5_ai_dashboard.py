"""
HCL Predictive Maintenance — Layer 5 AI Dashboard
===================================================
AIZCRM-inspired dark analytics dashboard with sidebar navigation,
Plotly charts, SVG gauges, and premium card-grid layout.

Business logic unchanged: SQLite reads, ai.predict(), AlertManager,
AuthManager and all permission gates are preserved exactly.
"""

import json
import os
import sqlite3
import sys
import time
import math
from datetime import datetime
from pathlib import Path

# ── sys.path safeguard ──────────────────────────────────────────
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from ml.predictor import PredictiveMaintenanceAI
from alerts.alert_manager import AlertManager
from auth.auth_manager import AuthManager
from ui.theme import (
    GLOBAL_CSS, PLOTLY_LAYOUT, BG_APP, BG_SIDEBAR, BG_CARD, BG_CARD_ALT,
    BG_INPUT, BORDER, BORDER_LIGHT, TEXT_PRIMARY, TEXT_HEADING, TEXT_MUTED,
    TEXT_SUBTLE, GREEN, GREEN_DIM, GREEN_GLOW, AMBER, AMBER_DIM, AMBER_GLOW,
    RED, RED_DIM, RED_GLOW, BLUE, BLUE_DIM, CYAN, CYAN_DIM, CYAN_GLOW,
    cond_color, cond_dim, cond_glow, cond_label, risk_color,
    card, pill, section_title, svg_health_ring, svg_sensor_rings,
    svg_anomaly_bar, svg_semicircle_gauge, gantt_bar,
)

# ── Page Config ─────────────────────────────────────────────────
st.set_page_config(
    page_title="HCL — Predictive Maintenance",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject global CSS ───────────────────────────────────────────
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── Core services ───────────────────────────────────────────────
DB_PATH = Path("data") / "machine_data.db"
ai = PredictiveMaintenanceAI()
alert_mgr = AlertManager()
auth_mgr = AuthManager()

# ── Session state defaults ──────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "page" not in st.session_state:
    st.session_state.page = "Overview"


# ── Database query (unchanged) ──────────────────────────────────
def fetch_recent_data(limit=100):
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT id, timestamp, machine_id, temperature_c, humidity_percent,
               vibration_g, rpm, load_percent, condition
        FROM machine_readings
        ORDER BY id DESC LIMIT {limit}
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ── Plotly chart builder ────────────────────────────────────────
def _plotly_line(df, col, color, title="", dash=None, fill=None, hover_fmt=None):
    """Build a dark-themed Plotly line chart for a sensor column with null safety."""
    fig = go.Figure()
    if df is not None and not df.empty and col in df.columns:
        df_clean = df.dropna(subset=[col, "timestamp"])
    else:
        df_clean = pd.DataFrame()

    if not df_clean.empty:
        fmt = hover_fmt or "%{y:.2f}"
        fig.add_trace(go.Scatter(
            x=df_clean["timestamp"], y=df_clean[col],
            mode="lines",
            line=dict(color=color, width=2, dash=dash or "solid"),
            fill=fill,
            fillcolor=f"rgba({_hex_rgb(color)},0.08)" if fill else None,
            hovertemplate=f"{fmt}<extra></extra>",
        ))
    else:
        fig.add_annotation(
            text="No telemetry data recorded",
            showarrow=False,
            font=dict(color=TEXT_MUTED, size=12, family="Poppins"),
            xref="paper", yref="paper", x=0.5, y=0.5
        )
    layout = {**PLOTLY_LAYOUT, "height": 240}
    if title:
        layout["title"] = dict(text=title, font=dict(size=13, color=TEXT_PRIMARY))
    fig.update_layout(**layout)
    return fig

def _hex_rgb(h):
    h = h.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


# ═══════════════════════════════════════════════════════════════
#  LOGIN PAGE
# ═══════════════════════════════════════════════════════════════
def render_login():
    # ── Split-screen: brand left, form right ────────────────────
    st.markdown(f"""
    <style>
    .login-brand {{
        background: linear-gradient(135deg, {BG_SIDEBAR} 0%, #15171C 100%);
        border-radius: 24px;
        padding: 48px 36px;
        display: flex; flex-direction: column; justify-content: center;
        align-items: center; text-align: center; min-height: 440px;
        border: 1px solid {BORDER};
        position: relative; overflow: hidden;
    }}
    .login-brand::before {{
        content: '';
        position: absolute; width: 220px; height: 220px;
        background: radial-gradient(circle, {GREEN_GLOW} 0%, transparent 70%);
        top: -40px; right: -40px; border-radius: 50%;
        animation: pulse-green 3s infinite;
    }}
    .login-card {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 24px;
        padding: 40px 32px;
    }}
    </style>
    """, unsafe_allow_html=True)

    cl, cr = st.columns([1.1, 1], gap="large")

    with cl:
        st.markdown(f"""
        <div class="login-brand">
            <div style="font-size:2.4rem; margin-bottom:8px;">⚙️</div>
            <div style="font-size:1.5rem; font-weight:700; color:{TEXT_HEADING};
                 font-family:Poppins,sans-serif; letter-spacing:-0.02em;">
                HCL Predictive Maintenance
            </div>
            <div style="font-size:0.85rem; color:{TEXT_MUTED}; margin-top:12px;
                 max-width:320px; line-height:1.6; font-family:Poppins,sans-serif;">
                Predict failures before they happen. AI-powered rotating machinery
                diagnostics &amp; real-time operational intelligence.
            </div>
            <div style="margin-top:24px;">
                {pill("AI/ML ENGINE", GREEN, font_size="0.7rem")}
                {pill("IoT ESP32", BLUE, font_size="0.7rem")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with cr:
        st.markdown(f"""
        <div style="margin-bottom:8px; margin-top:12px;">
            <span style="font-size:1.15rem; font-weight:700; color:{TEXT_HEADING};
                  font-family:Poppins,sans-serif;">Welcome back</span>
            <p style="font-size:0.8rem; color:{TEXT_MUTED}; margin-top:4px;
               font-family:Poppins,sans-serif;">
                Sign in to access the machinery analytics portal.
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g. admin",
                                     label_visibility="collapsed")
            password = st.text_input("Password", type="password",
                                     placeholder="Enter password",
                                     label_visibility="collapsed")
            submit = st.form_submit_button("Sign In", use_container_width=True)
            if submit:
                success, res = auth_mgr.authenticate(username, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user = res
                    st.rerun()
                else:
                    st.error(f"Authentication failed: {res}")

        st.markdown(f"""
        <div style="text-align:center; margin:16px 0 12px 0; padding-top:14px;
             border-top:1px solid {BORDER};">
            <span style="font-size:0.72rem; color:{TEXT_SUBTLE};
                  text-transform:uppercase; letter-spacing:0.06em;
                  font-family:Poppins,sans-serif;">Quick Demo Access</span>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        if c1.button("👑 Admin", use_container_width=True):
            _, res = auth_mgr.authenticate("admin", "admin123")
            st.session_state.authenticated = True
            st.session_state.user = res
            st.rerun()
        if c2.button("🛠️ Engineer", use_container_width=True):
            _, res = auth_mgr.authenticate("engineer", "engineer123")
            st.session_state.authenticated = True
            st.session_state.user = res
            st.rerun()
        if c3.button("👷 Operator", use_container_width=True):
            _, res = auth_mgr.authenticate("operator", "operator123")
            st.session_state.authenticated = True
            st.session_state.user = res
            st.rerun()


# ═══════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════════
def render_dashboard():
    user = st.session_state.user
    role = user.get("role", "operator")
    perms = user.get("permissions", {})

    # ── Load telemetry ──────────────────────────────────────────
    df = fetch_recent_data(limit=60)
    if df.empty:
        st.markdown(card(
            f'<div style="text-align:center;padding:32px;">'
            f'<div style="font-size:1.6rem;">📡</div>'
            f'<div style="font-size:1rem;font-weight:600;color:{TEXT_HEADING};'
            f'margin-top:8px;">No Telemetry Data</div>'
            f'<div style="font-size:0.82rem;color:{TEXT_MUTED};margin-top:4px;">'
            f'Ensure <code>layer3_storage.py</code> is running.</div></div>'
        ), unsafe_allow_html=True)
        return

    latest = df.iloc[0].to_dict()
    prediction = ai.predict(latest)

    cond = prediction.get("predicted_condition", "Healthy")
    risk = prediction.get("failure_risk_percent", 0.0)
    rul = prediction.get("estimated_rul_hours", 0.0)
    anomaly = prediction.get("anomaly_score", 0.0)
    conf = prediction.get("confidence_percent", 81.0) or 81.0
    root_cause = prediction.get("root_cause_analysis",
                                "Machine stationary / at rest")
    action_data = prediction.get("prescriptive_action",
                                 {"action": "ROUTINE MONITORING",
                                  "priority": "P3 - Normal",
                                  "timeframe": "Monthly"})

    active_alert_count = alert_mgr.get_active_count()
    cc = cond_color(cond)

    # health score = 100 - risk, capped 0..100
    health_score = max(0, min(100, 100 - risk))

    # ── SIDEBAR ─────────────────────────────────────────────────
    with st.sidebar:
        # Logo block
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px;
             padding:8px 4px 12px 4px;">
            <div style="width:34px;height:34px;border-radius:10px;
                 background:{GREEN};display:flex;align-items:center;
                 justify-content:center;font-size:1.1rem;font-weight:700;
                 color:#fff;">⚙</div>
            <div>
                <div style="font-weight:700;font-size:1rem;color:{TEXT_HEADING};
                     font-family:Poppins,sans-serif;letter-spacing:-0.02em;">
                    HCL PdM</div>
                <div style="font-size:0.62rem;color:{TEXT_MUTED};
                     text-transform:uppercase;letter-spacing:0.08em;
                     font-family:Poppins,sans-serif;">
                    Predictive Maintenance</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ── Vertical nav as rounded pills ───────────────────────
        nav_options = [
            ("Overview", "📊  Overview"),
            ("Trends", "📈  Trends"),
            ("Alerts", f"🔔  Alerts  ({active_alert_count})" if active_alert_count > 0 else "🔔  Alerts"),
            ("What-If", "🧪  What-If Sandbox"),
            ("AI Model", "🧠  AI Model"),
            ("Layers", "🏗️  Layers"),
        ]
        label_to_page = {disp: p_id for p_id, disp in nav_options}
        page_to_disp = {p_id: disp for p_id, disp in nav_options}

        cur_page = st.session_state.get("page", "Overview")
        if cur_page not in page_to_disp:
            cur_page = "Overview"
        cur_disp = page_to_disp[cur_page]

        selected_disp = st.radio(
            "Navigation",
            options=[disp for _, disp in nav_options],
            index=[disp for _, disp in nav_options].index(cur_disp),
            label_visibility="collapsed",
            key="main_sidebar_nav_radio"
        )
        target_page = label_to_page[selected_disp]
        if target_page != st.session_state.page:
            st.session_state.page = target_page
            st.rerun()

        st.divider()

        # ── Controls ────────────────────────────────────────────
        auto_refresh = st.checkbox("Auto Refresh (3s)",
                                   value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.rerun()

        st.divider()

        # ── Bottom light card: Machine Health ───────────────────
        st.markdown(f"""
        <div style="background:#F0F1F3;border-radius:18px;padding:18px 16px;
             margin-top:4px;">
            <div style="display:flex;align-items:center;gap:12px;">
                <div>{svg_health_ring(health_score, cc, 72)}</div>
                <div>
                    <div style="font-size:0.68rem;color:#5F6370;
                         text-transform:uppercase;letter-spacing:0.06em;
                         font-family:Poppins,sans-serif;">Machine Health</div>
                    <div style="font-size:0.92rem;font-weight:700;color:#1B1D23;
                         font-family:Poppins,sans-serif;">
                        {latest.get('machine_id','MOTOR_01')}</div>
                    <div style="font-size:0.68rem;color:#5F6370;margin-top:2px;
                         font-family:Poppins,sans-serif;">
                        RUL: {rul:.0f}h · AI: {conf:.0f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.write("")
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()


    # ── PAGE ROUTING & FRAGMENT CONTROLLER ──────────────────────
    page = st.session_state.page

    # Auto-refresh interval: 3s on live telemetry pages (Overview & Trends) when enabled
    refresh_interval = 3 if (st.session_state.get("auto_refresh", True) and page in ["Overview", "Trends"]) else None

    def _render_current_page(df_cur, latest_cur, pred_cur, cond_cur, risk_cur, rul_cur,
                             anomaly_cur, conf_cur, root_cause_cur, action_data_cur,
                             cc_cur, health_score_cur, active_alert_count_cur):
        if page == "Overview":
            _page_overview(df_cur, latest_cur, pred_cur, cond_cur, risk_cur, rul_cur, anomaly_cur,
                           conf_cur, root_cause_cur, action_data_cur, cc_cur, health_score_cur,
                           active_alert_count_cur, perms, user)
        elif page == "Trends":
            _page_trends(df_cur)
        elif page == "Alerts":
            _page_alerts(perms, user, active_alert_count_cur)
        elif page == "What-If":
            _page_sandbox(latest_cur)
        elif page == "AI Model":
            _page_model()
        elif page == "Layers":
            _page_layers()

    def _render_live_view():
        # Fresh query from SQLite on each fragment execution
        df_fresh = fetch_recent_data(limit=60)
        if df_fresh.empty:
            st.markdown(card(
                f'<div style="text-align:center;padding:32px;">'
                f'<div style="font-size:1.6rem;">📡</div>'
                f'<div style="font-size:1rem;font-weight:600;color:{TEXT_HEADING};'
                f'margin-top:8px;">No Telemetry Data</div>'
                f'<div style="font-size:0.82rem;color:{TEXT_MUTED};margin-top:4px;">'
                f'Ensure <code>layer3_storage.py</code> is running.</div></div>'
            ), unsafe_allow_html=True)
            return

        latest_fresh = df_fresh.iloc[0].to_dict()
        pred_fresh = ai.predict(latest_fresh)

        cond_fresh = pred_fresh.get("predicted_condition", "Healthy")
        risk_fresh = pred_fresh.get("failure_risk_percent", 0.0)
        rul_fresh = pred_fresh.get("estimated_rul_hours", 0.0)
        anomaly_fresh = pred_fresh.get("anomaly_score", 0.0)
        conf_fresh = pred_fresh.get("confidence_percent", 81.0) or 81.0
        root_cause_fresh = pred_fresh.get("root_cause_analysis",
                                         "Machine stationary / at rest")
        action_data_fresh = pred_fresh.get("prescriptive_action",
                                          {"action": "ROUTINE MONITORING",
                                           "priority": "P3 - Normal",
                                           "timeframe": "Monthly"})

        active_alert_cnt_fresh = alert_mgr.get_active_count()
        cc_fresh = cond_color(cond_fresh)
        health_score_fresh = max(0, min(100, 100 - risk_fresh))
        ts_display_fresh = latest_fresh.get("timestamp", "—")

        # ── User identity & avatar initials ─────────────────────────
        curr_user = st.session_state.get("user") or user or {}
        curr_role = curr_user.get("role", "operator")
        initials = "".join([w[0] for w in curr_user.get("full_name", "U").split()[:2]]).upper() or "U"

        # ── TOP HEADER BAR (Inside fragment to ensure LIVE timestamp updates) ──
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between;
             align-items:center; margin-bottom:18px; flex-wrap:wrap; gap:12px;">
            <div style="display:flex; align-items:center; gap:14px;">
                <span style="font-size:1.35rem; font-weight:700; color:{TEXT_HEADING};
                      font-family:Poppins,sans-serif; letter-spacing:-0.02em;">Dashboard</span>
                <div style="display:inline-flex; align-items:center; gap:6px;
                     background:{BG_CARD}; padding:4px 12px; border-radius:20px;
                     border:1px solid {BORDER}; font-size:0.75rem; color:{TEXT_MUTED};
                     font-family:Poppins,sans-serif;">
                    <span style="height:7px;width:7px;border-radius:50%;
                          background:{GREEN};display:inline-block;
                          animation:pulse-green 2s infinite;"></span>
                    LIVE · {ts_display_fresh}
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="display:flex; align-items:center; gap:8px;
                     background:{BG_CARD}; border:1px solid {BORDER};
                     border-radius:20px; padding:4px 12px; color:{TEXT_MUTED};
                     font-size:0.75rem; font-family:Poppins;">
                    <span>🔍</span>
                    <span>Search metrics...</span>
                </div>
                <div style="position:relative; background:{BG_CARD}; border:1px solid {BORDER};
                     width:34px; height:34px; border-radius:50%; display:flex;
                     align-items:center; justify-content:center; cursor:pointer;">
                    <span style="font-size:1.0rem;">🔔</span>
                    {'<span style="position:absolute;top:-3px;right:-3px;width:16px;height:16px;border-radius:50%;background:'+RED+';font-size:0.55rem;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-family:Poppins;">'+str(active_alert_cnt_fresh)+'</span>' if active_alert_cnt_fresh > 0 else ''}
                </div>
                {pill(cond_label(cond_fresh), cc_fresh, font_size="0.72rem")}
                <div style="display:flex; align-items:center; gap:8px;
                     background:{BG_CARD}; padding:4px 14px 4px 5px;
                     border-radius:22px; border:1px solid {BORDER};">
                    <div style="width:28px;height:28px;border-radius:50%;
                         background:{GREEN};display:flex;align-items:center;
                         justify-content:center;font-size:0.7rem;font-weight:700;
                         color:#fff;font-family:Poppins;">{initials}</div>
                    <div>
                        <div style="font-size:0.76rem;font-weight:600;
                             color:{TEXT_PRIMARY};font-family:Poppins;line-height:1.2;">
                            {curr_user.get('full_name','Operator')}</div>
                        <div style="font-size:0.6rem;color:{TEXT_SUBTLE};
                             font-family:Poppins;">{curr_role.title()}</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        _render_current_page(df_fresh, latest_fresh, pred_fresh, cond_fresh, risk_fresh,
                            rul_fresh, anomaly_fresh, conf_fresh, root_cause_fresh,
                            action_data_fresh, cc_fresh, health_score_fresh,
                            active_alert_cnt_fresh)

    if hasattr(st, "fragment"):
        @st.fragment(run_every=refresh_interval)
        def _fragment_view():
            _render_live_view()
        _fragment_view()
    else:
        _render_live_view()
        if refresh_interval:
            time.sleep(refresh_interval)
            st.rerun()



# ═══════════════════════════════════════════════════════════════
#  PAGE: OVERVIEW
# ═══════════════════════════════════════════════════════════════
def _page_overview(df, latest, prediction, cond, risk, rul, anomaly,
                   conf, root_cause, action_data, cc, health_score,
                   active_alert_count, perms, user):

    # ── Row 1: 4 metric cards (Risk, Vib, Humidity, Anomaly) ───────
    r1c1, r1c2, r1c3, r1c4 = st.columns(4, gap="medium")

    df_chron = df.sort_values("id", ascending=True) if not df.empty else df

    with r1c1:
        delta = risk - 25.0  # baseline comparison
        delta_color = RED if delta > 0 else GREEN
        delta_sign = "+" if delta > 0 else ""

        c_top1, c_top2 = st.columns([2.0, 1.3])
        with c_top1:
            st.markdown(f'<div style="font-size:0.72rem;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins,sans-serif;padding-top:4px;">Failure Risk</div>', unsafe_allow_html=True)
        with c_top2:
            if st.button("View chart ↗", key="btn_risk_trends", use_container_width=True):
                st.session_state.page = "Trends"
                st.rerun()

        st.markdown(card(
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
            f'<div>'
            f'<div style="font-size:2.4rem;font-weight:800;color:{TEXT_HEADING};font-family:Poppins,sans-serif;letter-spacing:-0.03em;">{risk:.1f}%</div>'
            f'<div style="margin-top:8px;">{pill(f"{delta_sign}{delta:.1f}% vs baseline", delta_color)}</div>'
            f'</div>'
            f'<div style="font-size:2.2rem;opacity:0.25;">📉</div>'
            f'</div>'
        ), unsafe_allow_html=True)

    with r1c2:
        # Live vibration mini chart with latest point bubble
        vib_val = latest.get("vibration_g", 0)
        try:
            vib_f = float(vib_val) if vib_val is not None and not (isinstance(vib_val, float) and math.isnan(vib_val)) else 0.0
        except (ValueError, TypeError):
            vib_f = 0.0
        st.markdown(card(
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
            f'<div>'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins,sans-serif;">Live Vibration</div>'
            f'<div style="font-size:2.2rem;font-weight:800;color:{TEXT_HEADING};font-family:Poppins,sans-serif;margin-top:4px;letter-spacing:-0.02em;">{vib_f:.3f}g</div>'
            f'</div>'
            f'{pill("● REALTIME", GREEN, font_size="0.65rem")}'
            f'</div>'
        ), unsafe_allow_html=True)
        if len(df_chron) > 1 and "vibration_g" in df_chron.columns:
            df_vib = df_chron.dropna(subset=["vibration_g", "timestamp"])
            if len(df_vib) > 1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_vib["timestamp"], y=df_vib["vibration_g"],
                    mode="lines", line=dict(color=GREEN, width=2.5, dash="dot"),
                    fill="tozeroy",
                    fillcolor="rgba(31,181,137,0.10)",
                    hovertemplate="%{y:.4f}g<extra></extra>",
                ))
                latest_x = df_vib["timestamp"].iloc[-1]
                latest_y = df_vib["vibration_g"].iloc[-1]
                fig.add_annotation(
                    x=latest_x, y=latest_y,
                    text=f"<b>{latest_y:.3f}g</b>",
                    showarrow=True,
                    arrowhead=0,
                    arrowcolor=GREEN,
                    ax=0, ay=-26,
                    bgcolor=GREEN,
                    bordercolor=GREEN,
                    borderwidth=1,
                    borderpad=4,
                    font=dict(color="#ffffff", size=10, family="Poppins"),
                )
                vib_layout = {
                    **PLOTLY_LAYOUT,
                    "height": 120,
                    "margin": dict(l=0, r=0, t=10, b=0),
                    "xaxis": dict(visible=False),
                    "yaxis": dict(visible=False),
                }
                fig.update_layout(**vib_layout)
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})

    with r1c3:
        # Live humidity metric card with latest SQLite reading and sparkline / empty state
        hum_raw = latest.get("humidity_percent")
        has_humidity = (hum_raw is not None and not (isinstance(hum_raw, float) and math.isnan(hum_raw)))
        if has_humidity:
            try:
                hum_f = float(hum_raw)
                hum_card_html = (
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                    f'<div>'
                    f'<div style="font-size:0.72rem;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins,sans-serif;">Live Humidity</div>'
                    f'<div style="font-size:2.2rem;font-weight:800;color:{TEXT_HEADING};font-family:Poppins,sans-serif;margin-top:4px;letter-spacing:-0.02em;">{hum_f:.1f}<span style="font-size:1.1rem;font-weight:600;color:{TEXT_MUTED};">% RH</span></div>'
                    f'</div>'
                    f'{pill("● SENSOR", CYAN, font_size="0.65rem")}'
                    f'</div>'
                )
            except (ValueError, TypeError):
                has_humidity = False

        if not has_humidity:
            hum_card_html = (
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                f'<div>'
                f'<div style="font-size:0.72rem;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins,sans-serif;">Live Humidity</div>'
                f'<div style="font-size:1.8rem;font-weight:700;color:{TEXT_MUTED};font-family:Poppins,sans-serif;margin-top:4px;">No Data</div>'
                f'<div style="font-size:0.68rem;color:{TEXT_SUBTLE};font-family:Poppins;margin-top:2px;">Awaiting DHT reading (% RH)</div>'
                f'</div>'
                f'{pill("○ UNAVAILABLE", TEXT_MUTED, font_size="0.65rem")}'
                f'</div>'
            )

        st.markdown(card(hum_card_html), unsafe_allow_html=True)

        if has_humidity and len(df_chron) > 1 and "humidity_percent" in df_chron.columns:
            df_hum = df_chron.dropna(subset=["humidity_percent", "timestamp"])
            if len(df_hum) > 1:
                fig_hum = go.Figure()
                fig_hum.add_trace(go.Scatter(
                    x=df_hum["timestamp"], y=df_hum["humidity_percent"],
                    mode="lines", line=dict(color=CYAN, width=2.5, dash="solid"),
                    fill="tozeroy",
                    fillcolor="rgba(56,189,248,0.10)",
                    hovertemplate="%{y:.1f}% RH<extra></extra>",
                ))
                latest_hx = df_hum["timestamp"].iloc[-1]
                latest_hy = df_hum["humidity_percent"].iloc[-1]
                fig_hum.add_annotation(
                    x=latest_hx, y=latest_hy,
                    text=f"<b>{latest_hy:.1f}%</b>",
                    showarrow=True,
                    arrowhead=0,
                    arrowcolor=CYAN,
                    ax=0, ay=-26,
                    bgcolor=CYAN,
                    bordercolor=CYAN,
                    borderwidth=1,
                    borderpad=4,
                    font=dict(color="#ffffff", size=10, family="Poppins"),
                )
                hum_layout = {
                    **PLOTLY_LAYOUT,
                    "height": 120,
                    "margin": dict(l=0, r=0, t=10, b=0),
                    "xaxis": dict(visible=False),
                    "yaxis": dict(visible=False),
                }
                fig_hum.update_layout(**hum_layout)
                st.plotly_chart(fig_hum, use_container_width=True,
                                config={"displayModeBar": False})

    with r1c4:
        # Anomaly score bar with zones
        st.markdown(card(
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">'
            f'<div>'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins,sans-serif;">Anomaly Score</div>'
            f'<div style="font-size:2.2rem;font-weight:800;color:{TEXT_HEADING};font-family:Poppins,sans-serif;margin-top:4px;letter-spacing:-0.02em;">{anomaly:.0f}'
            f'<span style="font-size:1rem;color:{TEXT_MUTED};font-weight:500;">/100</span></div>'
            f'</div>'
            f'<div style="font-size:2.0rem;opacity:0.25;">🎯</div>'
            f'</div>'
            f'{svg_anomaly_bar(anomaly, 320, 20)}'
        ), unsafe_allow_html=True)

    # ── Row 2: 3 cards ──────────────────────────────────────────
    r2c1, r2c2, r2c3 = st.columns(3, gap="medium")

    with r2c1:
        # Temperature & Load bar chart with 5-metric selector
        sel_col1, sel_col2 = st.columns([1.4, 1.6])
        with sel_col1:
            st.markdown(f'<div style="font-size:0.72rem;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins;padding-top:6px;">Metrics History</div>', unsafe_allow_html=True)
        with sel_col2:
            metric_choice = st.selectbox(
                "Metric",
                ["Temperature (°C)", "Humidity (% RH)", "Vibration (g)", "Load (%)", "RPM"],
                index=0,
                key="r2_metric_selector",
                label_visibility="collapsed"
            )

        if "Temp" in metric_choice:
            col_name, unit, bar_color = "temperature_c", "°C", GREEN
        elif "Humidity" in metric_choice:
            col_name, unit, bar_color = "humidity_percent", "% RH", CYAN
        elif "Vib" in metric_choice:
            col_name, unit, bar_color = "vibration_g", "g", AMBER
        elif "Load" in metric_choice:
            col_name, unit, bar_color = "load_percent", "%", BLUE
        else:
            col_name, unit, bar_color = "rpm", " RPM", RED

        df_bar = df.sort_values("id", ascending=True).tail(12) if not df.empty else df
        if len(df_bar) > 0 and col_name in df_bar.columns:
            df_bar_clean = df_bar.dropna(subset=[col_name, "timestamp"])
            if not df_bar_clean.empty:
                fig = go.Figure()
                n_bars = len(df_bar_clean)
                colors = [f"rgba(138,143,156,0.28)"] * (n_bars - 1) + [bar_color]
                pattern_shapes = ["/"] * (n_bars - 1) + [""]
                fig.add_trace(go.Bar(
                    x=df_bar_clean["timestamp"],
                    y=df_bar_clean[col_name],
                    marker=dict(color=colors, pattern=dict(shape=pattern_shapes), line=dict(color=BORDER, width=1)),
                    hovertemplate=f"%{{y:.1f}}{unit}<extra></extra>",
                ))
                latest_val = df_bar_clean[col_name].iloc[-1]
                fig.add_annotation(
                    x=df_bar_clean["timestamp"].iloc[-1], y=latest_val,
                    text=f"<b>{latest_val:.1f}{unit}</b>",
                    showarrow=True,
                    arrowhead=0,
                    arrowcolor=bar_color,
                    ax=0, ay=-22,
                    bgcolor=bar_color,
                    bordercolor=bar_color,
                    borderpad=4,
                    font=dict(color="#ffffff", size=10, family="Poppins"),
                )
                bar_layout = {
                    **PLOTLY_LAYOUT,
                    "height": 210,
                    "margin": dict(l=30, r=10, t=18, b=24),
                    "showlegend": False,
                    "xaxis": dict(visible=False),
                }
                fig.update_layout(**bar_layout)
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.markdown(f'<div style="text-align:center;padding:40px 0;color:{TEXT_MUTED};font-size:0.8rem;font-family:Poppins;">No historical data for {metric_choice}</div>', unsafe_allow_html=True)

    with r2c2:
        # Segmented/tick-mark health gauge with soft glow
        glow_style = f"border:1px solid {cond_glow(cond)};" if cond != "Healthy" else ""
        st.markdown(card(
            f'<div style="text-align:center;">'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins,sans-serif;margin-bottom:8px;">Machine Health Index</div>'
            f'{svg_semicircle_gauge(health_score, cc, "Health Score", 190)}'
            f'<div style="margin-top:10px;">{pill(cond_label(cond), cc)}</div>'
            f'</div>',
            extra_style=glow_style
        ), unsafe_allow_html=True)

    with r2c3:
        # Concentric sensor rings (5 metrics) + Incident Log preview
        temp_val = latest.get("temperature_c", 0)
        hum_raw = latest.get("humidity_percent")
        vib_val = latest.get("vibration_g", 0)
        load_val = latest.get("load_percent", 0)
        rpm_val = latest.get("rpm", 0)

        try:
            temp_f = float(temp_val) if temp_val is not None and not (isinstance(temp_val, float) and math.isnan(temp_val)) else 0.0
        except (ValueError, TypeError):
            temp_f = 0.0
        try:
            vib_f = float(vib_val) if vib_val is not None and not (isinstance(vib_val, float) and math.isnan(vib_val)) else 0.0
        except (ValueError, TypeError):
            vib_f = 0.0
        try:
            load_f = float(load_val) if load_val is not None and not (isinstance(load_val, float) and math.isnan(load_val)) else 0.0
        except (ValueError, TypeError):
            load_f = 0.0
        try:
            rpm_f = float(rpm_val) if rpm_val is not None and not (isinstance(rpm_val, float) and math.isnan(rpm_val)) else 0.0
        except (ValueError, TypeError):
            rpm_f = 0.0

        has_hum = hum_raw is not None and not (isinstance(hum_raw, float) and math.isnan(hum_raw))
        if has_hum:
            try:
                hum_f = float(hum_raw)
                hum_str = f"<b>{hum_f:.1f}% RH</b>"
                hum_ring_val = hum_f
            except (ValueError, TypeError):
                has_hum = False
                hum_str = f'<span style="color:{TEXT_MUTED};">N/A</span>'
                hum_ring_val = 0.0
        else:
            hum_str = f'<span style="color:{TEXT_MUTED};">N/A</span>'
            hum_ring_val = 0.0

        rings_svg = svg_sensor_rings([
            ("Temp", temp_f, 95.0, AMBER),
            ("Humidity", hum_ring_val, 100.0, CYAN),
            ("Vib", vib_f, 0.5, GREEN),
            ("Load", load_f, 100.0, BLUE),
            ("RPM", rpm_f, 1600.0, RED),
        ], 130, center_text=cond[:4].upper(), center_color=cc)

        st.markdown(card(
            f'<div style="display:flex;align-items:center;gap:14px;">'
            f'<div>{rings_svg}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.70rem;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins,sans-serif;margin-bottom:4px;">5-Sensor Load (% Limit)</div>'
            f'<div style="font-size:0.72rem;color:{TEXT_PRIMARY};font-family:Poppins,sans-serif;line-height:1.75;">'
            f'<span style="color:{AMBER};">●</span> Temp: <b>{temp_f:.1f}°C</b> ({min(100, temp_f/95.0*100):.0f}%)<br>'
            f'<span style="color:{CYAN};">●</span> Humidity: {hum_str}<br>'
            f'<span style="color:{GREEN};">●</span> Vib: <b>{vib_f:.3f}g</b> ({min(100, vib_f/0.5*100):.0f}%)<br>'
            f'<span style="color:{BLUE};">●</span> Load: <b>{load_f:.0f}%</b><br>'
            f'<span style="color:{RED};">●</span> RPM: <b>{rpm_f:.0f}</b> ({min(100, rpm_f/1600.0*100):.0f}%)'
            f'</div></div></div>'
        ), unsafe_allow_html=True)

        recent_alerts = alert_mgr.get_recent_alerts(limit=3)
        if recent_alerts:
            alert_rows = ""
            for i, a in enumerate(recent_alerts):
                sc = RED if a.get("severity") == "CRITICAL" else AMBER
                highlight = f"background:{BG_CARD_ALT};border:1px solid {BORDER_LIGHT};" if i == 0 else "border:1px solid transparent;"
                ts = a.get("timestamp", "")
                ts_short = ts.split("T")[-1] if "T" in ts else (ts.split(" ")[-1] if " " in ts else ts)
                alert_rows += (
                    f'<div style="display:flex;align-items:center;gap:10px;padding:6px 10px;border-radius:12px;margin-bottom:4px;{highlight}">'
                    f'<div style="width:24px;height:24px;border-radius:50%;background:rgba({_hex_rgb(sc)},0.15);display:flex;align-items:center;justify-content:center;font-size:0.7rem;flex-shrink:0;">{"🔴" if a.get("severity")=="CRITICAL" else "🟡"}</div>'
                    f'<div style="flex:1;min-width:0;">'
                    f'<div style="font-size:0.70rem;font-weight:600;color:{TEXT_PRIMARY};font-family:Poppins;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{a.get("root_cause","Alert")[:34]}</div>'
                    f'<div style="font-size:0.60rem;color:{TEXT_SUBTLE};font-family:Poppins;">#{a.get("id","")} · Logged: {ts_short} · {a.get("status","ACTIVE")}</div></div>'
                    f'<span style="color:{TEXT_MUTED};font-size:0.75rem;">•••</span>'
                    f'</div>'
                )
            status_tag = f'<span style="font-size:0.62rem;color:{GREEN};font-weight:600;">● Live: {cond}</span>' if cond == "Healthy" else f'<span style="font-size:0.62rem;color:{RED};font-weight:600;">● Active Anomaly</span>'
            note_html = f'<div style="font-size:0.60rem;color:{TEXT_MUTED};font-style:italic;margin-top:6px;font-family:Poppins;">Past incident log; current machine condition is {cond}.</div>' if cond == "Healthy" else ''
            st.markdown(f"""
            <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:18px;padding:12px 14px;margin-bottom:14px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:0.68rem;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins;">Incident Log</span>
                    {status_tag}
                </div>
                {alert_rows}
                {note_html}
            </div>
            """, unsafe_allow_html=True)

    # ── Row 3: Wide maintenance tasks card ──────────────────────
    st.markdown(section_title("Maintenance Overview",
                              "Root-cause timeline & next maintenance actions"),
                unsafe_allow_html=True)

    r3l, r3r = st.columns([1.2, 1], gap="medium")

    with r3l:
        total_alerts = alert_mgr.get_active_count()
        all_recent = alert_mgr.get_recent_alerts(limit=50)
        resolved = sum(1 for a in all_recent if a.get("status") in ["RESOLVED", "ACKNOWLEDGED"])
        total_recent = max(len(all_recent), 1)
        pct_resolved = min(100.0, (resolved / total_recent) * 100)
        rul_days = rul / 24.0

        mood = "😍" if cond == "Healthy" else ("😐" if cond == "Warning" else "😰")
        mood_text = ("Machine is running smoothly" if cond == "Healthy"
                     else ("Warning conditions detected" if cond == "Warning"
                           else "Fault detected — action required"))
        mood_color = cc

        st.markdown(card(
            f'<div style="display:flex;justify-content:space-around;gap:20px;margin-bottom:16px;">'
            f'<div style="text-align:center;">'
            f'<div style="font-size:1.6rem;font-weight:800;color:{TEXT_HEADING};font-family:Poppins;">{pct_resolved:.0f}%</div>'
            f'<div style="font-size:0.68rem;color:{TEXT_MUTED};font-family:Poppins;">Tasks Addressed</div></div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:1.6rem;font-weight:800;color:{TEXT_HEADING};font-family:Poppins;">{rul_days:.1f}d</div>'
            f'<div style="font-size:0.68rem;color:{TEXT_MUTED};font-family:Poppins;">Remaining Life</div></div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:1.6rem;font-weight:800;color:{TEXT_HEADING};font-family:Poppins;">{conf:.0f}%</div>'
            f'<div style="font-size:0.68rem;color:{TEXT_MUTED};font-family:Poppins;">AI Confidence</div></div>'
            f'</div>'
            # Status banner
            f'<div style="background:{BG_CARD_ALT};border-radius:12px;padding:10px 16px;display:flex;align-items:center;gap:12px;margin-bottom:14px;border:1px solid {BORDER};">'
            f'<span style="font-size:1.3rem;">{mood}</span>'
            f'<span style="font-size:0.82rem;color:{mood_color};font-weight:600;font-family:Poppins;">{mood_text}</span></div>'
            # Next action card
            f'<div style="background:{BG_INPUT};border-radius:14px;padding:14px 18px;display:flex;align-items:center;gap:14px;border:1px solid {BORDER_LIGHT};">'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.65rem;color:{TEXT_SUBTLE};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins;">Next Recommended Action</div>'
            f'<div style="font-size:0.88rem;font-weight:700;color:{TEXT_HEADING};font-family:Poppins;margin-top:2px;">{action_data["action"]}</div>'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};font-family:Poppins;margin-top:2px;">{action_data["priority"]} · {action_data["timeframe"]}</div>'
            f'</div>'
            f'</div>'
        ), unsafe_allow_html=True)

        # Interactive buttons below Next Action
        btn_c1, btn_c2, _ = st.columns([1.3, 1.3, 2.5])
        if perms.get("acknowledge_alerts", True):
            if btn_c1.button("✓ Acknowledge", key="overview_ack_btn", use_container_width=True):
                if recent_alerts:
                    alert_mgr.acknowledge_alert(recent_alerts[0]["id"], user.get("full_name", "Operator"))
                    st.toast("Alert acknowledged")
                    st.rerun()
        if btn_c2.button("✕ Dismiss", key="overview_dismiss_btn", use_container_width=True):
            st.toast("Action dismissed")

    with r3r:
        # Maintenance progress + Gantt bars with vertical progress
        all_recent = alert_mgr.get_recent_alerts(limit=50)
        resolved = sum(1 for a in all_recent if a.get("status") in ["RESOLVED", "ACKNOWLEDGED"])
        total_recent = max(len(all_recent), 1)
        progress_pct = min(100.0, (resolved / total_recent) * 100)

        # Derived bar lengths from actual machine metrics
        inspect_pct = min(95.0, max(10.0, risk * 1.1))
        cooling_pct = min(95.0, max(8.0, (latest.get("temperature_c", 30) - 20) / 75 * 100))
        balance_pct = min(95.0, max(5.0, latest.get("vibration_g", 0.025) / 0.5 * 100))
        overhaul_pct = min(95.0, max(5.0, 100 - health_score))

        st.markdown(card(
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
            f'<div>'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.06em;font-family:Poppins;">Maintenance Plan</div>'
            f'<div style="font-size:0.95rem;font-weight:700;color:{TEXT_HEADING};font-family:Poppins;margin-top:2px;">{resolved}/{total_recent} tasks addressed</div>'
            f'</div>'
            f'{pill(f"{progress_pct:.0f}% Done", GREEN, font_size="0.7rem")}'
            f'</div>'
            # Progress bar
            f'<div style="background:{BG_INPUT};border-radius:8px;height:8px;margin-bottom:18px;overflow:hidden;">'
            f'<div style="background:{GREEN};height:8px;border-radius:8px;width:{progress_pct:.0f}%;transition:width 0.6s;"></div>'
            f'</div>'
            # Gantt bars with hatched pattern
            f'{gantt_bar("Inspect Bearing", inspect_pct, RED)}'
            f'{gantt_bar("Check Cooling", cooling_pct, BLUE)}'
            f'{gantt_bar("Re-balance", balance_pct, GREEN)}'
            f'{gantt_bar("Overhaul Plan", overhaul_pct, AMBER)}'
        ), unsafe_allow_html=True)


    # ── Root cause & prescriptive row ───────────────────────────
    rc1, rc2 = st.columns(2, gap="medium")
    with rc1:
        st.markdown(card(
            f'<div style="font-size:0.72rem;color:{GREEN};font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.06em;'
            f'font-family:Poppins;margin-bottom:6px;">🔍 Root Cause Diagnostic</div>'
            f'<div style="font-size:0.92rem;font-weight:600;color:{TEXT_HEADING};'
            f'font-family:Poppins;">{root_cause}</div>'
            f'<div style="font-size:0.75rem;color:{TEXT_MUTED};margin-top:8px;'
            f'font-family:Poppins;">'
            f'Anomaly: <b style="color:{TEXT_PRIMARY};">{anomaly}/100</b> · '
            f'Risk: <b style="color:{TEXT_PRIMARY};">{risk}%</b> · '
            f'Engine: {prediction.get("model_version","—")}</div>'
        ), unsafe_allow_html=True)
    with rc2:
        st.markdown(card(
            f'<div style="font-size:0.72rem;color:{AMBER};font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.06em;'
            f'font-family:Poppins;margin-bottom:6px;">📋 Prescriptive Action</div>'
            f'<div style="font-size:0.92rem;font-weight:600;color:{TEXT_HEADING};'
            f'font-family:Poppins;">{action_data["action"]}</div>'
            f'<div style="font-size:0.75rem;color:{TEXT_MUTED};margin-top:8px;'
            f'font-family:Poppins;">'
            f'Priority: <b style="color:{AMBER};">{action_data["priority"]}</b> · '
            f'Timeframe: <b>{action_data["timeframe"]}</b></div>'
        ), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  PAGE: TRENDS
# ═══════════════════════════════════════════════════════════════
def _page_trends(df):
    st.markdown(section_title("Time-Series Sensor Trends",
                              "Live rolling history from ESP32 telemetry"),
                unsafe_allow_html=True)

    df_chron = df.sort_values("id", ascending=True) if not df.empty else df

    # Row 1: Temperature & Humidity
    tc1, tc2 = st.columns(2, gap="medium")
    with tc1:
        st.markdown(card(
            f'<div style="font-size:0.72rem;font-weight:600;color:{AMBER};'
            f'text-transform:uppercase;font-family:Poppins;margin-bottom:4px;">'
            f'🔥 Temperature (°C)</div>'
        ), unsafe_allow_html=True)
        fig = _plotly_line(df_chron, "temperature_c", AMBER, "", hover_fmt="%{y:.1f}°C")
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})

    with tc2:
        st.markdown(card(
            f'<div style="font-size:0.72rem;font-weight:600;color:{CYAN};'
            f'text-transform:uppercase;font-family:Poppins;margin-bottom:4px;">'
            f'💧 Humidity (% RH)</div>'
        ), unsafe_allow_html=True)
        fig = _plotly_line(df_chron, "humidity_percent", CYAN, "", hover_fmt="%{y:.1f}% RH")
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})

    # Row 2: Vibration & RPM
    tc3, tc4 = st.columns(2, gap="medium")
    with tc3:
        st.markdown(card(
            f'<div style="font-size:0.72rem;font-weight:600;color:{GREEN};'
            f'text-transform:uppercase;font-family:Poppins;margin-bottom:4px;">'
            f'⚡ Vibration (g RMS)</div>'
        ), unsafe_allow_html=True)
        fig = _plotly_line(df_chron, "vibration_g", GREEN, "",
                           dash="dot", fill="tozeroy", hover_fmt="%{y:.3f}g")
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})

    with tc4:
        st.markdown(card(
            f'<div style="font-size:0.72rem;font-weight:600;color:{BLUE};'
            f'text-transform:uppercase;font-family:Poppins;margin-bottom:4px;">'
            f'🔄 RPM</div>'
        ), unsafe_allow_html=True)
        fig = _plotly_line(df_chron, "rpm", BLUE, "", hover_fmt="%{y:.0f} RPM")
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})

    # Row 3: Load (%) & 5-Sensor Telemetry Summary Card
    tc5, tc6 = st.columns(2, gap="medium")
    with tc5:
        st.markdown(card(
            f'<div style="font-size:0.72rem;font-weight:600;color:{RED};'
            f'text-transform:uppercase;font-family:Poppins;margin-bottom:4px;">'
            f'📊 Dynamic Load (%)</div>'
        ), unsafe_allow_html=True)
        fig = _plotly_line(df_chron, "load_percent", RED, "", hover_fmt="%{y:.1f}%")
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})

    with tc6:
        if not df_chron.empty:
            l_row = df_chron.iloc[-1]
            t_val = l_row.get("temperature_c")
            h_val = l_row.get("humidity_percent")
            v_val = l_row.get("vibration_g")
            r_val = l_row.get("rpm")
            ld_val = l_row.get("load_percent")

            t_avg = df_chron["temperature_c"].mean() if "temperature_c" in df_chron.columns else 0.0
            t_max = df_chron["temperature_c"].max() if "temperature_c" in df_chron.columns else 0.0

            has_h = "humidity_percent" in df_chron.columns and not df_chron["humidity_percent"].dropna().empty
            if has_h:
                h_avg = df_chron["humidity_percent"].mean()
                h_max = df_chron["humidity_percent"].max()
                h_last_str = f"{float(h_val):.1f}% RH" if h_val is not None and not pd.isna(h_val) else "N/A"
                h_sub = f"Avg: {h_avg:.1f}% · Max: {h_max:.1f}%"
            else:
                h_last_str = "N/A"
                h_sub = "Sensor offline or awaiting DHT"

            v_avg = df_chron["vibration_g"].mean() if "vibration_g" in df_chron.columns else 0.0
            v_max = df_chron["vibration_g"].max() if "vibration_g" in df_chron.columns else 0.0

            r_val_f = float(r_val) if r_val is not None and not pd.isna(r_val) else 0.0
            ld_val_f = float(ld_val) if ld_val is not None and not pd.isna(ld_val) else 0.0
            t_val_f = float(t_val) if t_val is not None and not pd.isna(t_val) else 0.0
            v_val_f = float(v_val) if v_val is not None and not pd.isna(v_val) else 0.0
        else:
            t_val_f, v_val_f, r_val_f, ld_val_f = 0.0, 0.0, 0.0, 0.0
            t_avg, t_max, v_avg, v_max = 0.0, 0.0, 0.0, 0.0
            h_last_str, h_sub = "N/A", "No records"

        st.markdown(card(
            f'<div style="font-size:0.72rem;font-weight:600;color:{TEXT_MUTED};'
            f'text-transform:uppercase;font-family:Poppins;margin-bottom:12px;">'
            f'📋 5-Sensor Telemetry Summary</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-family:Poppins;">'
            f'<div style="background:{BG_CARD_ALT};padding:12px 14px;border-radius:14px;border:1px solid {BORDER_LIGHT};">'
            f'<div style="font-size:0.65rem;color:{TEXT_MUTED};text-transform:uppercase;">Temperature</div>'
            f'<div style="font-size:1.15rem;font-weight:700;color:{AMBER};margin-top:2px;">{t_val_f:.1f} °C</div>'
            f'<div style="font-size:0.62rem;color:{TEXT_SUBTLE};margin-top:2px;">Avg: {t_avg:.1f}°C · Max: {t_max:.1f}°C</div>'
            f'</div>'
            f'<div style="background:{BG_CARD_ALT};padding:12px 14px;border-radius:14px;border:1px solid {BORDER_LIGHT};">'
            f'<div style="font-size:0.65rem;color:{TEXT_MUTED};text-transform:uppercase;">Humidity</div>'
            f'<div style="font-size:1.15rem;font-weight:700;color:{CYAN};margin-top:2px;">{h_last_str}</div>'
            f'<div style="font-size:0.62rem;color:{TEXT_SUBTLE};margin-top:2px;">{h_sub}</div>'
            f'</div>'
            f'<div style="background:{BG_CARD_ALT};padding:12px 14px;border-radius:14px;border:1px solid {BORDER_LIGHT};">'
            f'<div style="font-size:0.65rem;color:{TEXT_MUTED};text-transform:uppercase;">Vibration</div>'
            f'<div style="font-size:1.15rem;font-weight:700;color:{GREEN};margin-top:2px;">{v_val_f:.3f} g</div>'
            f'<div style="font-size:0.62rem;color:{TEXT_SUBTLE};margin-top:2px;">Avg: {v_avg:.3f}g · Max: {v_max:.3f}g</div>'
            f'</div>'
            f'<div style="background:{BG_CARD_ALT};padding:12px 14px;border-radius:14px;border:1px solid {BORDER_LIGHT};">'
            f'<div style="font-size:0.65rem;color:{TEXT_MUTED};text-transform:uppercase;">Speed & Load</div>'
            f'<div style="font-size:1.15rem;font-weight:700;color:{BLUE};margin-top:2px;">{r_val_f:.0f} RPM</div>'
            f'<div style="font-size:0.62rem;color:{TEXT_SUBTLE};margin-top:2px;">Dynamic Load: {ld_val_f:.0f}%</div>'
            f'</div>'
            f'</div>'
        ), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  PAGE: ALERTS
# ═══════════════════════════════════════════════════════════════
def _page_alerts(perms, user, active_alert_count):
    st.markdown(section_title(
        "Alert Center",
        f"{active_alert_count} active unacknowledged alerts"
    ), unsafe_allow_html=True)

    alerts = alert_mgr.get_recent_alerts(limit=25)

    if not alerts:
        st.markdown(card(
            f'<div style="text-align:center;padding:32px;">'
            f'<div style="font-size:1.6rem;">✨</div>'
            f'<div style="font-size:0.95rem;font-weight:600;color:{GREEN};'
            f'margin-top:8px;font-family:Poppins;">No Active Alerts</div>'
            f'<div style="font-size:0.8rem;color:{TEXT_MUTED};margin-top:4px;'
            f'font-family:Poppins;">All telemetry within normal parameters.</div>'
            f'</div>'
        ), unsafe_allow_html=True)
        return

    for alt in alerts:
        sev = alt["severity"]
        sc = RED if sev == "CRITICAL" else AMBER
        status = alt.get("status", "ACTIVE")
        status_colors = {"ACTIVE": RED, "ACKNOWLEDGED": AMBER, "RESOLVED": GREEN}
        st_col = status_colors.get(status, TEXT_MUTED)

        glow = f"box-shadow: inset 3px 0 0 {sc};" if status == "ACTIVE" else ""

        st.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid {BORDER};
             border-radius:16px;padding:16px 20px;margin-bottom:10px;{glow}
             transition:transform 0.2s;">
            <div style="display:flex;justify-content:space-between;
                 align-items:center;">
                <div style="display:flex;align-items:center;gap:10px;">
                    {pill(sev, sc)}
                    <span style="font-weight:600;color:{TEXT_PRIMARY};
                          font-size:0.85rem;font-family:Poppins;">
                        Asset: {alt.get('machine_id','MOTOR_01')}</span>
                </div>
                <div style="font-size:0.72rem;color:{TEXT_MUTED};
                     font-family:Poppins;">
                    {alt.get('timestamp','')} ·
                    <b style="color:{st_col};">{status}</b>
                </div>
            </div>
            <div style="font-size:0.82rem;color:{TEXT_PRIMARY};margin:6px 0;
                 font-family:Poppins;">
                <b>Root Cause:</b> {alt.get('root_cause','')}
            </div>
            <div style="font-size:0.7rem;color:{TEXT_SUBTLE};font-family:Poppins;">
                Temp: {alt.get('temperature_c','')}°C ·
                Vib: {alt.get('vibration_g','')}g ·
                RPM: {alt.get('rpm','')} ·
                Risk: {alt.get('failure_risk_percent','')}%
            </div>
        </div>
        """, unsafe_allow_html=True)

        can_ack = (status == "ACTIVE") and perms.get("acknowledge_alerts", True)
        can_res = (status in ["ACTIVE", "ACKNOWLEDGED"]) and perms.get("resolve_alerts", False)
        if can_ack or can_res:
            ac1, ac2, ac_fill = st.columns([1.2, 1.2, 3.6])
            if can_ack:
                if ac1.button(f"✓ Acknowledge #{alt['id']}",
                              key=f"ack_{alt['id']}",
                              use_container_width=True):
                    alert_mgr.acknowledge_alert(alt["id"],
                                                user.get("full_name", "Operator"))
                    st.rerun()
            if can_res:
                if ac2.button(f"✓ Resolve #{alt['id']}",
                              key=f"res_{alt['id']}",
                              use_container_width=True):
                    alert_mgr.resolve_alert(alt["id"],
                                            user.get("full_name", "Engineer"))
                    st.rerun()


# ═══════════════════════════════════════════════════════════════
#  PAGE: WHAT-IF SANDBOX
# ═══════════════════════════════════════════════════════════════
def _page_sandbox(latest):
    st.markdown(section_title(
        "What-If Simulation Sandbox",
        "Evaluate hypothetical scenarios without affecting production"
    ), unsafe_allow_html=True)

    sc1, sc2 = st.columns(2, gap="medium")
    with sc1:
        st.markdown(card(
            f'<div style="font-size:0.72rem;color:{GREEN};font-weight:600;'
            f'text-transform:uppercase;font-family:Poppins;'
            f'margin-bottom:6px;">Input Parameters</div>'
        ), unsafe_allow_html=True)
        sim_temp = st.slider("Temperature (°C)", 20.0, 95.0,
                             float(latest.get("temperature_c", 27.5)), 0.5)
        sim_vib = st.slider("Vibration (g RMS)", 0.010, 0.500,
                            float(latest.get("vibration_g", 0.025)), 0.005)
        sim_rpm = st.slider("Shaft Speed (RPM)", 0, 1600, 1450, 25)

    with sc2:
        st.markdown(card(
            f'<div style="font-size:0.72rem;color:{GREEN};font-weight:600;'
            f'text-transform:uppercase;font-family:Poppins;'
            f'margin-bottom:6px;">Environment</div>'
        ), unsafe_allow_html=True)
        sim_load = st.slider("Dynamic Load (%)", 0.0, 100.0, 50.0, 1.0)
        sim_hum = st.slider("Humidity (%)", 20.0, 90.0,
                            float(latest.get("humidity_percent", 50.0)), 1.0)

    sim_input = {
        "temperature_c": sim_temp, "vibration_g": sim_vib,
        "rpm": sim_rpm, "load_percent": sim_load,
        "humidity_percent": sim_hum, "machine_id": "MOTOR_01",
    }
    sim_pred = ai.predict(sim_input)
    s_cond = sim_pred["predicted_condition"]
    s_risk = sim_pred["failure_risk_percent"]
    s_rul = sim_pred["estimated_rul_hours"]
    s_cause = sim_pred["root_cause_analysis"]
    s_action = sim_pred["prescriptive_action"]["action"]
    s_cc = cond_color(s_cond)

    # Results as 3 big-number cards
    rc1, rc2, rc3 = st.columns(3, gap="medium")
    with rc1:
        st.markdown(card(
            f'<div style="text-align:center;">'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};'
            f'text-transform:uppercase;font-family:Poppins;">Condition</div>'
            f'<div style="font-size:1.8rem;font-weight:800;color:{s_cc};'
            f'font-family:Poppins;margin-top:6px;">{s_cond}</div></div>'
        ), unsafe_allow_html=True)
    with rc2:
        st.markdown(card(
            f'<div style="text-align:center;">'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};'
            f'text-transform:uppercase;font-family:Poppins;">Failure Risk</div>'
            f'<div style="font-size:1.8rem;font-weight:800;color:{risk_color(s_risk)};'
            f'font-family:Poppins;margin-top:6px;">{s_risk}%</div></div>'
        ), unsafe_allow_html=True)
    with rc3:
        st.markdown(card(
            f'<div style="text-align:center;">'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};'
            f'text-transform:uppercase;font-family:Poppins;">RUL</div>'
            f'<div style="font-size:1.8rem;font-weight:800;color:{TEXT_HEADING};'
            f'font-family:Poppins;margin-top:6px;">{s_rul}'
            f'<span style="font-size:0.9rem;color:{TEXT_MUTED};"> Hrs</span>'
            f'</div></div>'
        ), unsafe_allow_html=True)

    # Highlighted diagnosis card
    st.markdown(card(
        f'<div style="border-left:4px solid {s_cc};padding-left:14px;">'
        f'<div style="font-size:0.72rem;color:{s_cc};font-weight:600;'
        f'text-transform:uppercase;font-family:Poppins;">Simulation Diagnosis</div>'
        f'<div style="font-size:0.88rem;font-weight:600;color:{TEXT_HEADING};'
        f'font-family:Poppins;margin-top:6px;">{s_cause}</div>'
        f'<div style="font-size:0.78rem;color:{TEXT_MUTED};'
        f'font-family:Poppins;margin-top:4px;">'
        f'Prescribed: <b style="color:{GREEN};">{s_action}</b></div></div>'
    ), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  PAGE: AI MODEL
# ═══════════════════════════════════════════════════════════════
def _page_model():
    st.markdown(section_title(
        "AI Model Explainability",
        "Random Forest classification & RUL regression pipeline"
    ), unsafe_allow_html=True)

    metrics = ai.metrics
    mc1, mc2, mc3 = st.columns(3, gap="medium")
    with mc1:
        acc = metrics.get("accuracy", 1.0) * 100
        st.markdown(card(
            f'<div style="text-align:center;">'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};'
            f'text-transform:uppercase;font-family:Poppins;">Classifier Accuracy</div>'
            f'<div style="font-size:2rem;font-weight:800;color:{GREEN};'
            f'font-family:Poppins;margin-top:6px;">{acc:.1f}%</div>'
            f'<div style="font-size:0.68rem;color:{TEXT_SUBTLE};'
            f'font-family:Poppins;margin-top:2px;">Random Forest Ensemble</div></div>'
        ), unsafe_allow_html=True)
    with mc2:
        r2 = metrics.get("r2_score", 0.996)
        st.markdown(card(
            f'<div style="text-align:center;">'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};'
            f'text-transform:uppercase;font-family:Poppins;">RUL Regressor R²</div>'
            f'<div style="font-size:2rem;font-weight:800;color:{BLUE};'
            f'font-family:Poppins;margin-top:6px;">{r2:.4f}</div>'
            f'<div style="font-size:0.68rem;color:{TEXT_SUBTLE};'
            f'font-family:Poppins;margin-top:2px;">Holdout Goodness of Fit</div></div>'
        ), unsafe_allow_html=True)
    with mc3:
        ts = metrics.get("training_samples", 7600)
        st.markdown(card(
            f'<div style="text-align:center;">'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};'
            f'text-transform:uppercase;font-family:Poppins;">Training Samples</div>'
            f'<div style="font-size:2rem;font-weight:800;color:{TEXT_HEADING};'
            f'font-family:Poppins;margin-top:6px;">{ts:,}</div>'
            f'<div style="font-size:0.68rem;color:{TEXT_SUBTLE};'
            f'font-family:Poppins;margin-top:2px;">Synthesized & Calibrated</div></div>'
        ), unsafe_allow_html=True)

    # Feature importance chart
    feat_imp = metrics.get("feature_importances", {})
    if feat_imp:
        imp_df = pd.DataFrame(list(feat_imp.items()),
                              columns=["Feature", "Importance"])
        imp_df = imp_df.sort_values("Importance", ascending=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=imp_df["Feature"], x=imp_df["Importance"],
            orientation="h",
            marker=dict(
                color=imp_df["Importance"],
                colorscale=[[0, BG_CARD_ALT], [1, GREEN]],
            ),
            hovertemplate="%{x:.4f}<extra></extra>",
        ))
        feat_layout = {
            **PLOTLY_LAYOUT,
            "height": 340,
            "margin": dict(l=140, r=20, t=40, b=20),
            "title": dict(text="Feature Importance Rankings",
                          font=dict(size=13, color=TEXT_PRIMARY)),
        }
        fig.update_layout(**feat_layout)
        st.markdown(card(
            f'<div id="feat-chart"></div>'
        ), unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})


# ═══════════════════════════════════════════════════════════════
#  PAGE: ARCHITECTURE LAYERS
# ═══════════════════════════════════════════════════════════════
def _page_layers():
    st.markdown(section_title(
        "System Architecture",
        "IoT-to-AI pipeline layer overview"
    ), unsafe_allow_html=True)

    layers = [
        ("1", "Sensors", "DHT11, MPU6050, IR Tachometer", GREEN, "Physical"),
        ("2", "MQTT Transport", "HiveMQ Cloud TLS/SSL", GREEN, "Network"),
        ("3", "SQLite Storage", "Real-time telemetry ingestion", GREEN, "Data"),
        ("4", "Node-RED Runtime", "Flow orchestration engine", GREEN, "Edge"),
        ("5", "AI Model & Portal", "Random Forest + Streamlit", GREEN, "Cloud"),
        ("6", "ESP32 Hardware", "Motor lockout active", AMBER, "Device"),
    ]

    for num, title, desc, color, tag in layers:
        st.markdown(card(
            f'<div style="display:flex;align-items:center;gap:16px;">'
            f'<div style="width:38px;height:38px;border-radius:12px;'
            f'background:rgba({_hex_rgb(color)},0.12);display:flex;'
            f'align-items:center;justify-content:center;font-size:0.85rem;'
            f'font-weight:700;color:{color};font-family:Poppins;flex-shrink:0;">'
            f'L{num}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.88rem;font-weight:600;color:{TEXT_HEADING};'
            f'font-family:Poppins;">{title}</div>'
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};'
            f'font-family:Poppins;margin-top:2px;">{desc}</div></div>'
            f'{pill(tag, color, font_size="0.65rem")}'
            f'<span style="color:{color};font-size:0.8rem;">●</span>'
            f'</div>'
        ), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if not st.session_state.authenticated:
        render_login()
    else:
        render_dashboard()
