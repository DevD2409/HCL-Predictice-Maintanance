import os
import sys
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from ui.theme import (
    CYAN, CYAN_DIM, CYAN_GLOW, svg_sensor_rings, PLOTLY_LAYOUT
)
from layer5_ai_dashboard import (
    fetch_recent_data, _plotly_line, _hex_rgb, DB_PATH
)

def test_sensor_rings():
    print("[1] Testing svg_sensor_rings with 5 sensors...")
    # Normal 5 sensors
    svg1 = svg_sensor_rings([
        ("Temp", 27.5, 95.0, "#F5A524"),
        ("Humidity", 52.0, 100.0, CYAN),
        ("Vib", 0.025, 0.5, "#1FB589"),
        ("Load", 45.0, 100.0, "#2D6BFF"),
        ("RPM", 1450, 1600.0, "#F0553F"),
    ], 130, center_text="OK", center_color="#1FB589")
    assert "<svg" in svg1 and "</svg>" in svg1
    assert "Humidity" not in svg1 # svg contains rings and center text
    assert "OK" in svg1
    # Check 5 rings generated (10 circles: 5 backgrounds + 5 fills + 1 center circle = 11 circles)
    assert svg1.count("<circle") == 11
    print("    -> Passed! 5 concentric rings rendered correctly.")

    # None / NaN values
    svg2 = svg_sensor_rings([
        ("Temp", None, 95.0, "#F5A524"),
        ("Humidity", float("nan"), 100.0, CYAN),
        ("Vib", 0.0, 0.5, "#1FB589"),
        ("Load", None, 100.0, "#2D6BFF"),
        ("RPM", 0, 1600.0, "#F0553F"),
    ], 130, center_text="WARN", center_color="#F5A524")
    assert "<svg" in svg2
    assert "WARN" in svg2
    print("    -> Passed! None/NaN values safely handled.")

def test_plotly_line():
    print("[2] Testing _plotly_line with various dataframe inputs...")
    # Normal data
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "timestamp": ["12:00:01", "12:00:02", "12:00:03"],
        "humidity_percent": [48.5, 49.0, 50.2],
        "temperature_c": [26.1, 26.2, 26.3],
    })
    fig = _plotly_line(df, "humidity_percent", CYAN, "Humidity (% RH)", hover_fmt="%{y:.1f}% RH")
    assert fig is not None
    assert len(fig.data) == 1
    assert fig.data[0].line.color == CYAN
    assert fig.data[0].hovertemplate == "%{y:.1f}% RH<extra></extra>"
    print("    -> Passed! Normal line chart produced.")

    # With nulls in target column
    df_nulls = pd.DataFrame({
        "id": [1, 2, 3],
        "timestamp": ["12:00:01", "12:00:02", "12:00:03"],
        "humidity_percent": [48.5, None, 50.2],
    })
    fig2 = _plotly_line(df_nulls, "humidity_percent", CYAN, "Humidity (% RH)")
    assert len(fig2.data) == 1
    assert len(fig2.data[0].x) == 2  # dropped None row
    print("    -> Passed! Null handling works (2 valid points plotted).")

    # Empty dataframe
    fig_empty = _plotly_line(pd.DataFrame(), "humidity_percent", CYAN)
    assert len(fig_empty.data) == 0
    assert len(fig_empty.layout.annotations) == 1
    assert "No telemetry data" in fig_empty.layout.annotations[0].text
    print("    -> Passed! Empty dataframe renders clean empty state annotation.")

def test_db_readings():
    print("[3] Testing fetch_recent_data() from SQLite...")
    df = fetch_recent_data(limit=10)
    assert not df.empty, "Database table machine_readings is empty"
    assert "humidity_percent" in df.columns, "humidity_percent column missing from query"
    latest = df.iloc[0].to_dict()
    print(f"    -> Latest row: id={latest['id']}, timestamp={latest['timestamp']}, "
          f"temp={latest['temperature_c']}°C, hum={latest['humidity_percent']}%, "
          f"vib={latest['vibration_g']}g, rpm={latest['rpm']}, load={latest['load_percent']}%")
    assert latest["humidity_percent"] is not None
    print("    -> Passed! humidity_percent successfully retrieved from live SQLite database.")

if __name__ == "__main__":
    test_sensor_rings()
    test_plotly_line()
    test_db_readings()
    print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
