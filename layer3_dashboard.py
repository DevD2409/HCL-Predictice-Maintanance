import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# -------------------------------------------------
# Database path
# -------------------------------------------------

DATABASE = Path("data/machine_data.db")


# -------------------------------------------------
# Streamlit settings
# -------------------------------------------------

st.set_page_config(
    page_title="Layer 3 Predictive Maintenance",
    page_icon="⚙️",
    layout="wide"
)


st.title("⚙️ Predictive Maintenance Dashboard")

st.caption(
    "Layer 3 — MQTT → HiveMQ → SQLite → Live Dashboard"
)


# -------------------------------------------------
# Read latest records from SQLite
# -------------------------------------------------

def get_machine_data(limit=60):

    if not DATABASE.exists():
        return pd.DataFrame()

    try:

        connection = sqlite3.connect(
            DATABASE,
            timeout=5
        )

        query = """
            SELECT
                id,
                timestamp,
                machine_id,
                temperature_c,
                humidity_percent,
                vibration_g,
                rpm,
                load_percent,
                condition

            FROM machine_readings

            ORDER BY id DESC

            LIMIT ?
        """

        df = pd.read_sql_query(
            query,
            connection,
            params=(limit,)
        )

        connection.close()


        # Database query gives newest first.
        # Reverse so graphs display oldest → newest.
        df = df.iloc[::-1].reset_index(drop=True)

        return df


    except Exception as error:

        st.error(
            f"Database read error: {error}"
        )

        return pd.DataFrame()


# -------------------------------------------------
# Count total database readings
# -------------------------------------------------

def get_total_readings():

    try:

        connection = sqlite3.connect(
            DATABASE,
            timeout=5
        )

        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM machine_readings"
        )

        total = cursor.fetchone()[0]

        connection.close()

        return total

    except:
        return 0


# -------------------------------------------------
# Live section
# -------------------------------------------------

@st.fragment(run_every="1s")
def live_dashboard():

    df = get_machine_data(
        limit=60
    )


    if df.empty:

        st.info(
            "Waiting for machine data in SQLite..."
        )

        return


    # ---------------------------------------------
    # Prepare timestamp
    # ---------------------------------------------

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )


    latest = df.iloc[-1]

    condition = str(
        latest["condition"]
    )


    # ---------------------------------------------
    # Database status
    # ---------------------------------------------

    st.success(
        "SQLite Database Connected"
    )


    # ---------------------------------------------
    # Machine condition
    # ---------------------------------------------

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


    # ---------------------------------------------
    # Basic information
    # ---------------------------------------------

    st.write(
        f"**Machine:** {latest['machine_id']}"
    )

    st.write(
        f"**Last Reading:** {latest['timestamp']}"
    )


    # ---------------------------------------------
    # Metrics
    # ---------------------------------------------

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
        "Database Records",
        get_total_readings()
    )


    st.divider()


    # ---------------------------------------------
    # Use timestamp as graph index
    # ---------------------------------------------

    graph_df = df.copy()

    graph_df = graph_df.dropna(
        subset=["timestamp"]
    )

    graph_df = graph_df.set_index(
        "timestamp"
    )


    # ---------------------------------------------
    # Temperature + vibration
    # ---------------------------------------------

    left, right = st.columns(2)


    with left:

        st.subheader(
            "Temperature Trend"
        )

        st.line_chart(
            graph_df[
                ["temperature_c"]
            ]
        )


    with right:

        st.subheader(
            "Vibration Trend"
        )

        st.line_chart(
            graph_df[
                ["vibration_g"]
            ]
        )


    # ---------------------------------------------
    # RPM + Load
    # ---------------------------------------------

    left2, right2 = st.columns(2)


    with left2:

        st.subheader(
            "RPM Trend"
        )

        st.line_chart(
            graph_df[
                ["rpm"]
            ]
        )


    with right2:

        st.subheader(
            "Load Trend"
        )

        st.line_chart(
            graph_df[
                ["load_percent"]
            ]
        )


    # ---------------------------------------------
    # Latest database rows
    # ---------------------------------------------

    st.subheader(
        "Latest SQLite Records"
    )


    display_df = df.tail(10).iloc[::-1]


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


live_dashboard()