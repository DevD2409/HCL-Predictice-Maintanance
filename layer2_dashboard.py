import pandas as pd
import streamlit as st

from mqtt_receiver import MQTTReceiver


# -------------------------------------------------
# Streamlit page settings
# -------------------------------------------------

st.set_page_config(
    page_title="Layer 2 Predictive Maintenance",
    page_icon="⚙️",
    layout="wide"
)


st.title(
    "⚙️ Predictive Maintenance Dashboard"
)

st.caption(
    "Layer 2 — Direct MQTT → HiveMQ → Live Dashboard"
)


# -------------------------------------------------
# Create MQTT receiver only ONCE
# -------------------------------------------------

@st.cache_resource
def create_receiver():

    receiver = MQTTReceiver()

    receiver.start()

    return receiver


receiver = create_receiver()


# -------------------------------------------------
# Live dashboard
# -------------------------------------------------

@st.fragment(run_every="1s")
def live_dashboard():

    latest, history = receiver.get_data()


    # No MQTT data yet
    if latest is None:

        st.info(
            "Waiting for MQTT machine data..."
        )

        return


    # -------------------------------------------------
    # Connection information
    # -------------------------------------------------

    if receiver.connected:

        st.success(
            "MQTT Connected to HiveMQ Cloud"
        )

    else:

        st.warning(
            "MQTT connection not established"
        )


    # -------------------------------------------------
    # Machine condition
    # -------------------------------------------------

    condition = latest.get(
        "condition",
        "Unknown"
    )


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
    # Machine information
    # -------------------------------------------------

    st.write(
        f"**Machine:** {latest.get('machine_id')}"
    )

    st.write(
        f"**Last Reading:** {latest.get('timestamp')}"
    )


    # -------------------------------------------------
    # Metrics
    # -------------------------------------------------

    col1, col2, col3 = st.columns(3)


    col1.metric(
        "Temperature",
        f"{latest.get('temperature_c', 0):.2f} °C"
    )


    col2.metric(
        "Vibration",
        f"{latest.get('vibration_g', 0):.3f} g"
    )


    col3.metric(
        "RPM",
        f"{latest.get('rpm', 0)}"
    )


    col4, col5, col6 = st.columns(3)


    col4.metric(
        "Humidity",
        f"{latest.get('humidity_percent', 0):.2f} %"
    )


    col5.metric(
        "Load",
        f"{latest.get('load_percent', 0):.2f} %"
    )


    col6.metric(
        "Stored Readings",
        len(history)
    )


    # -------------------------------------------------
    # Need at least 2 readings for graphs
    # -------------------------------------------------

    if len(history) < 2:

        st.info(
            "Collecting more readings for graphs..."
        )

        return


    # -------------------------------------------------
    # Convert memory data to DataFrame
    # -------------------------------------------------

    df = pd.DataFrame(history)


    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )


    df = df.dropna(
        subset=["timestamp"]
    )


    df = df.set_index(
        "timestamp"
    )


    st.divider()


    # -------------------------------------------------
    # Temperature and vibration
    # -------------------------------------------------

    left, right = st.columns(2)


    with left:

        st.subheader(
            "Temperature Trend"
        )

        st.line_chart(
            df[
                ["temperature_c"]
            ]
        )


    with right:

        st.subheader(
            "Vibration Trend"
        )

        st.line_chart(
            df[
                ["vibration_g"]
            ]
        )


    # -------------------------------------------------
    # RPM and Load
    # -------------------------------------------------

    left2, right2 = st.columns(2)


    with left2:

        st.subheader(
            "RPM Trend"
        )

        st.line_chart(
            df[
                ["rpm"]
            ]
        )


    with right2:

        st.subheader(
            "Load Trend"
        )

        st.line_chart(
            df[
                ["load_percent"]
            ]
        )


    # -------------------------------------------------
    # Recent readings
    # -------------------------------------------------

    st.subheader(
        "Latest MQTT Readings"
    )


    display_df = pd.DataFrame(
        history[-10:]
    )


    display_df = display_df.iloc[::-1]


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


live_dashboard()