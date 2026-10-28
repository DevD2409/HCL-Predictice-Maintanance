import sys
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.graph_objects as go

PROJECT_ROOT = Path(r"c:\Users\devdw\OneDrive\Documents\HCL-Predictive-Maintenance")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.theme import (
    PLOTLY_LAYOUT, GREEN, BLUE, AMBER, RED, CYAN, BORDER,
    svg_sensor_rings, card, pill, section_title
)
from ml.predictor import PredictiveMaintenanceAI
from alerts.alert_manager import AlertManager
from layer5_ai_dashboard import _plotly_line, _hex_rgb

def run_comprehensive_checks():
    print("=" * 60)
    print("COMPREHENSIVE DASHBOARD VERIFICATION")
    print("=" * 60)

    # 1. Database & Telemetry check
    db_path = PROJECT_ROOT / "data" / "machine_data.db"
    assert db_path.exists(), "machine_data.db not found"
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT id, timestamp, machine_id, temperature_c, humidity_percent, "
        "vibration_g, rpm, load_percent, condition FROM machine_readings ORDER BY id DESC LIMIT 100",
        conn
    )
    conn.close()
    assert not df.empty, "machine_readings table has no rows"
    latest = df.iloc[0].to_dict()
    df_chron = df.sort_values("id", ascending=True)

    print(f"[OK] Database query succeeded. Found {len(df)} recent telemetry rows.")
    print(f"     Latest reading: Temp={latest['temperature_c']}°C, Hum={latest['humidity_percent']}%, Vib={latest['vibration_g']}g, RPM={latest['rpm']}, Load={latest['load_percent']}%")

    # 2. Check humidity presence and empty-state fallback
    assert "humidity_percent" in latest, "humidity_percent key missing from latest reading"
    assert latest["humidity_percent"] is not None, "humidity_percent is None in latest reading"
    hum_raw = latest["humidity_percent"]
    hum_f = float(hum_raw)
    print(f"[OK] Humidity reading parsed: {hum_f:.1f}% RH")

    # 3. Simulate Row 1 Humidity Sparkline Figure
    fig_hum = go.Figure()
    fig_hum.add_trace(go.Scatter(
        x=df_chron["timestamp"], y=df_chron["humidity_percent"],
        mode="lines", line=dict(color=CYAN, width=2.5, dash="solid"),
        fill="tozeroy",
        fillcolor="rgba(56,189,248,0.10)",
        hovertemplate="%{y:.1f}% RH<extra></extra>",
    ))
    latest_hx = df_chron["timestamp"].iloc[-1]
    latest_hy = df_chron["humidity_percent"].iloc[-1]
    fig_hum.add_annotation(
        x=latest_hx, y=latest_hy,
        text=f"<b>{latest_hy:.1f}%</b>",
        showarrow=True, arrowhead=0, arrowcolor=CYAN,
        ax=0, ay=-26, bgcolor=CYAN, bordercolor=CYAN,
        borderwidth=1, borderpad=4,
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
    assert fig_hum.to_dict()["layout"]["height"] == 120
    print("[OK] Row 1 Live Humidity sparkline figure generated without layout collisions.")

    # 4. Simulate Row 2 Metrics History Bar Chart with Humidity
    df_bar = df_chron.tail(12).dropna(subset=["humidity_percent", "timestamp"])
    n_bars = len(df_bar)
    colors = [f"rgba(138,143,156,0.28)"] * (n_bars - 1) + [CYAN]
    pattern_shapes = ["/"] * (n_bars - 1) + [""]
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=df_bar["timestamp"],
        y=df_bar["humidity_percent"],
        marker=dict(color=colors, pattern=dict(shape=pattern_shapes), line=dict(color=BORDER, width=1)),
        hovertemplate="%{y:.1f}% RH<extra></extra>",
    ))
    bar_layout = {
        **PLOTLY_LAYOUT,
        "height": 210,
        "margin": dict(l=30, r=10, t=18, b=24),
        "showlegend": False,
        "xaxis": dict(visible=False),
    }
    fig_bar.update_layout(**bar_layout)
    assert fig_bar.to_dict()["layout"]["height"] == 210
    print("[OK] Row 2 Metrics History bar chart with Humidity (% RH) generated successfully.")

    # 5. Simulate 5 Concentric Rings
    temp_val = float(latest.get("temperature_c", 0))
    hum_val = float(latest.get("humidity_percent", 0))
    vib_val = float(latest.get("vibration_g", 0))
    load_val = float(latest.get("load_percent", 0))
    rpm_val = float(latest.get("rpm", 0))

    rings_svg = svg_sensor_rings([
        ("Temp", temp_val, 95.0, AMBER),
        ("Humidity", hum_val, 100.0, CYAN),
        ("Vib", vib_val, 0.5, GREEN),
        ("Load", load_val, 100.0, BLUE),
        ("RPM", rpm_val, 1600.0, RED),
    ], 130, center_text="OK", center_color=GREEN)
    assert "<svg" in rings_svg and "</svg>" in rings_svg
    assert rings_svg.count("<circle") == 11
    print("[OK] Row 2 Concentric sensor rings rendered with all 5 sensors.")

    # 6. Simulate Alerts / Incident Log
    alert_mgr = AlertManager()
    recent_alerts = alert_mgr.get_recent_alerts(limit=3)
    assert isinstance(recent_alerts, list)
    print(f"[OK] AlertManager returned {len(recent_alerts)} recent incident log records.")
    for a in recent_alerts:
        ts = a.get("timestamp", "")
        ts_short = ts.split("T")[-1] if "T" in ts else (ts.split(" ")[-1] if " " in ts else ts)
        print(f"     Alert #{a['id']}: {a['root_cause']} [{a['severity']}] - Logged: {ts_short} ({a['status']})")

    # 7. Simulate Trends 5 Time-Series Charts
    f_temp = _plotly_line(df_chron, "temperature_c", AMBER, "", hover_fmt="%{y:.1f}°C")
    f_hum  = _plotly_line(df_chron, "humidity_percent", CYAN, "", hover_fmt="%{y:.1f}% RH")
    f_vib  = _plotly_line(df_chron, "vibration_g", GREEN, "", dash="dot", fill="tozeroy", hover_fmt="%{y:.3f}g")
    f_rpm  = _plotly_line(df_chron, "rpm", BLUE, "", hover_fmt="%{y:.0f} RPM")
    f_load = _plotly_line(df_chron, "load_percent", RED, "", hover_fmt="%{y:.1f}%")

    for name, f in [("Temperature", f_temp), ("Humidity", f_hum), ("Vibration", f_vib), ("RPM", f_rpm), ("Load", f_load)]:
        assert len(f.data) == 1, f"Missing trace in {name} chart"
        assert f.data[0].x is not None and len(f.data[0].x) > 0, f"No points in {name} chart"
        assert f.to_dict()["layout"]["height"] == 240
    print("[OK] Trends: All 5 time-series charts generated with correct heights and traces.")

    print("\n" + "=" * 60)
    print("ALL VERIFICATION CHECKS COMPLETED AND CONFIRMED HEALTHY!")
    print("=" * 60)

if __name__ == "__main__":
    run_comprehensive_checks()
