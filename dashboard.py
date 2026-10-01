from pathlib import Path

import pandas as pd
import streamlit as st


CSV_FILE = Path("data/machine_data.csv")


# -------------------------------------------------
# Page configuration
# -------------------------------------------------

st.set_page_config(
    page_title="Predictive Maintenance Dashboard",
    page_icon="⚙️",
    layout="wide"
)


st.title("⚙️ Predictive Maintenance Dashboard")

st.caption(
    "HCL Mini Project — Rotating Machinery Condition Monitoring"
)


# -------------------------------------------------
# Live dashboard section
# -------------------------------------------------

@st.fragment(run_every="2s")
def live_dashboard():

    if not CSV_FILE.exists():

        st.info(
            "Waiting for machine data..."
        )

        return


    try:

        df = pd.read_csv(CSV_FILE)

    except Exception:

        st.warning(
            "Reading latest sensor data..."
        )

        return


    if df.empty:

        st.info(
            "No machine readings available."
        )

        return


    # Convert timestamp
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )


    # Latest reading
    latest = df.iloc[-1]

    condition = str(
        latest["condition"]
    )


    # -------------------------------------------------
    # Machine status
    # -------------------------------------------------

    if condition == "Healthy":

        st.success(
            "Machine Status: HEALTHY"
        )

    elif condition == "Warning":

        st.warning(
            "Machine Status: WARNING"
        )

    else:

        st.error(
            "Machine Status: FAULT"
        )


    # -------------------------------------------------
    # Metrics
    # -------------------------------------------------

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Temperature",
        f"{latest['temperature_c']:.2f} °C"
    )

    col2.metric(
        "Vibration",
        f"{latest['vibration_g']:.3f} g"
    )

    col3.metric(
        "RPM",
        f"{latest['rpm']:.0f}"
    )


    col4, col5, col6 = st.columns(3)

    col4.metric(
        "Humidity",
        f"{latest['humidity_percent']:.2f} %"
    )

    col5.metric(
        "Load",
        f"{latest['load_percent']:.2f} %"
    )

    col6.metric(
        "Machine",
        latest["machine_id"]
    )


    st.divider()


    # -------------------------------------------------
    # Only latest 60 readings
    # -------------------------------------------------

    recent = df.tail(60).copy()

    recent = recent.set_index(
        "timestamp"
    )


    # -------------------------------------------------
    # Temperature + Vibration
    # -------------------------------------------------

    left, right = st.columns(2)


    with left:

        st.subheader(
            "Temperature Trend"
        )

        st.line_chart(
            recent[
                ["temperature_c"]
            ]
        )


    with right:

        st.subheader(
            "Vibration Trend"
        )

        st.line_chart(
            recent[
                ["vibration_g"]
            ]
        )


    # -------------------------------------------------
    # RPM + Load
    # -------------------------------------------------

    left2, right2 = st.columns(2)


    with left2:

        st.subheader(
            "RPM Trend"
        )

        st.line_chart(
            recent[
                ["rpm"]
            ]
        )


    with right2:

        st.subheader(
            "Load Trend"
        )

        st.line_chart(
            recent[
                ["load_percent"]
            ]
        )


    # -------------------------------------------------
    # Latest readings table
    # -------------------------------------------------

    st.subheader(
        "Latest Machine Readings"
    )

    display_df = df.tail(10).iloc[::-1]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


live_dashboard()