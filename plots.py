from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


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


def rolling_mean_std_plot(df: pd.DataFrame, city: str):
    """График скользящего среднего и стандартного отклонения с полосой ±2σ."""
    data = df[df["city"] == city].sort_values("timestamp").copy()
    
    # Убираем NaN значения для корректного отображения
    data = data.dropna(subset=["rolling_mean", "rolling_std"])
    
    if data.empty:
        # Если нет данных, возвращаем пустой график
        fig = go.Figure()
        fig.update_layout(title=f"Rolling statistics — {city} (нет данных)")
        return fig
    
    fig = go.Figure()
    
    # Температура
    fig.add_trace(go.Scatter(
        x=data["timestamp"],
        y=data["temperature"],
        mode="lines",
        name="Температура",
        line=dict(color="blue", width=1),
        opacity=0.6
    ))
    
    # Скользящее среднее
    fig.add_trace(go.Scatter(
        x=data["timestamp"],
        y=data["rolling_mean"],
        mode="lines",
        name="Скользящее среднее (30 дней)",
        line=dict(color="green", width=2)
    ))
    
    # Верхняя граница ±2σ
    fig.add_trace(go.Scatter(
        x=data["timestamp"],
        y=data["rolling_mean"] + 2 * data["rolling_std"],
        mode="lines",
        name="+2σ",
        line=dict(color="orange", width=1, dash="dash"),
        opacity=0.7
    ))
    
    # Нижняя граница -2σ
    fig.add_trace(go.Scatter(
        x=data["timestamp"],
        y=data["rolling_mean"] - 2 * data["rolling_std"],
        mode="lines",
        name="-2σ",
        line=dict(color="orange", width=1, dash="dash"),
        opacity=0.7,
        fill="tonexty",
        fillcolor="rgba(255, 165, 0, 0.1)"
    ))
    
    # Аномалии
    anomalies = data[data["is_anomaly_rolling"]]
    if not anomalies.empty:
        fig.add_trace(go.Scatter(
            x=anomalies["timestamp"],
            y=anomalies["temperature"],
            mode="markers",
            name="Аномалии (rolling)",
            marker=dict(color="red", size=8, symbol="x")
        ))
    
    fig.update_layout(
        title=f"Скользящее среднее и стандартное отклонение — {city}",
        xaxis_title="Дата",
        yaxis_title="Температура (°C)",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    return fig


def rolling_std_plot(df: pd.DataFrame, city: str):
    """Отдельный график скользящего стандартного отклонения."""
    data = df[df["city"] == city].sort_values("timestamp").copy()
    
    # Убираем NaN значения
    data = data.dropna(subset=["rolling_std"])
    
    if data.empty:
        fig = go.Figure()
        fig.update_layout(title=f"Скользящее стандартное отклонение — {city} (нет данных)")
        return fig
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data["timestamp"],
        y=data["rolling_std"],
        mode="lines",
        name="Скользящее σ (30 дней)",
        line=dict(color="purple", width=2),
        fill="tozeroy",
        fillcolor="rgba(128, 0, 128, 0.2)"
    ))
    
    fig.update_layout(
        title=f"Скользящее стандартное отклонение — {city}",
        xaxis_title="Дата",
        yaxis_title="Стандартное отклонение (°C)",
        hovermode="x unified"
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


