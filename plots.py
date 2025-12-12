from __future__ import annotations

import pandas as pd
import plotly.express as px


def line_with_anomalies(df: pd.DataFrame, city: str):
    data = df[df["city"] == city].sort_values("timestamp")
    fig = px.line(
        data,
        x="timestamp",
        y="temperature",
        title=f"Temperature timeline — {city}",
    )
    anomalies = data[data["is_anomaly_rolling"] | data["is_anomaly_season"]]
    if not anomalies.empty:
        fig.add_scatter(
            x=anomalies["timestamp"],
            y=anomalies["temperature"],
            mode="markers",
            marker=dict(color="red", size=10, symbol="x"),
            name="Anomaly",
        )
    return fig


def seasonal_boxplot(df: pd.DataFrame, city: str):
    data = df[df["city"] == city]
    fig = px.box(
        data,
        x="season",
        y="temperature",
        title=f"Seasonal distribution — {city}",
        points="all",
    )
    return fig

