from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
import numpy as np
from numpy import polyfit, poly1d
import plotly.graph_objects as go
from dotenv import load_dotenv

from analysis import (
    prepare_features,
    season_from_timestamp,
    current_season_mean_std,
    is_temp_normal,
    load_data,
)
from plots import line_with_anomalies, seasonal_boxplot, rolling_mean_std_plot, rolling_std_plot
from weather_api import fetch_current_weather, fetch_current_weather_async, WeatherError

# Загружаем .env файл если он есть
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


DATA_PATH = Path(__file__).parent / "data" / "temperature_data.csv"


@st.cache_data
def load_sample_data() -> pd.DataFrame:
    return load_data(str(DATA_PATH))


def main():
    # Информация об авторе в боковой панели
    st.sidebar.markdown("### Автор: Соловьев Сергей")
    
    st.title("Температурные ряды и текущая погода (OpenWeatherMap)")
    st.write("Загрузите CSV или используйте демонстрационные данные.")

    uploaded = st.file_uploader("Загрузить CSV", type=["csv"])
    if uploaded:
        df = load_data(uploaded)
    else:
        df = load_sample_data()

    if df.empty:
        st.error("Данных нет.")
        return

    # ВЫВОД из экспериментов: для CPU-bound задач (rolling, вычисления) последовательная обработка оптимальна
    # ThreadPoolExecutor не эффективен из-за GIL, накладные расходы превышают выгоду
    # См. experiments.ipynb для детального анализа
    df_features = prepare_features(df)
    cities = sorted(df_features["city"].unique())
    city = st.selectbox("Город", cities)

    api_key_input = st.text_input("OpenWeatherMap API key", type="password")
    # ВЫВОД из экспериментов: async даёт ускорение в 18-19 раз для множественных запросов
    # Для одного запроса async тоже быстрее (~77%), поэтому используем async по умолчанию
    use_async = st.toggle("Использовать асинхронный запрос", value=True)

    if st.button("Обновить текущую погоду"):
        # Проверка: если ключ не введен, данные для текущей погоды не показываются
        if not api_key_input:
            st.warning("Введите API ключ OpenWeatherMap для получения текущей погоды.")
        else:
            try:
                # РЕКОМЕНДАЦИЯ: Использовать async для всех API запросов (см. experiments.ipynb)
                # Async особенно эффективен для I/O операций и не блокирует интерфейс Streamlit
                if use_async:
                    weather = asyncio.run(fetch_current_weather_async(city, api_key_input))
                else:
                    # Sync запросы блокируют выполнение и медленнее (см. эксперименты)
                    weather = fetch_current_weather(city, api_key_input)
                st.success(
                    f"Текущая температура: {weather['temp']} °C, "
                    f"{weather.get('description', '').capitalize()}"
                )
                now_season = season_from_timestamp(pd.Timestamp.now())
                mean, std = current_season_mean_std(df_features, city, now_season)
                if pd.isna(mean):
                    st.info("Недостаточно данных для сезона.")
                else:
                    normal = is_temp_normal(weather["temp"], mean, std)
                    st.write(
                        f"Сезонный диапазон ({now_season}): {mean:.1f} ± 2σ≈{2*std:.1f}; "
                        f"статус: {'норма' if normal else 'аномалия'}"
                    )
            except WeatherError as exc:
                # Специальная обработка ошибки 401 (некорректный API ключ)
                error_msg = str(exc)
                if "401" in error_msg or "Invalid API key" in error_msg:
                    st.error(f"❌ {error_msg}")
                else:
                    st.error(f"Ошибка API: {error_msg}")
            except Exception as exc:  # safety net
                st.error(f"Ошибка: {exc}")

    st.subheader("Временной ряд с аномалиями")
    st.plotly_chart(line_with_anomalies(df_features, city), use_container_width=True)

    st.subheader("Скользящее среднее и стандартное отклонение")
    st.plotly_chart(rolling_mean_std_plot(df_features, city), use_container_width=True)
    st.caption("График показывает температуру, скользящее среднее (окно 30 дней) и полосу ±2σ для выявления аномалий.")

    st.subheader("Скользящее стандартное отклонение")
    st.plotly_chart(rolling_std_plot(df_features, city), use_container_width=True)
    st.caption("График показывает изменение волатильности температуры (скользящее σ за 30 дней).")

    st.subheader("Сезонное распределение")
    st.plotly_chart(seasonal_boxplot(df_features, city), use_container_width=True)

    # Описательная статистика по историческим данным
    st.subheader("Описательная статистика")
    city_data = df_features[df_features["city"] == city]["temperature"]
    stats_cols = st.columns(4)
    with stats_cols[0]:
        st.metric("Средняя температура", f"{city_data.mean():.2f} °C")
    with stats_cols[1]:
        st.metric("Медиана", f"{city_data.median():.2f} °C")
    with stats_cols[2]:
        st.metric("Стандартное отклонение", f"{city_data.std():.2f} °C")
    with stats_cols[3]:
        st.metric("Диапазон", f"{city_data.min():.1f} - {city_data.max():.1f} °C")
    
    # Долгосрочный тренд (линейная регрессия)
    st.subheader("Долгосрочный тренд")
    city_df = df_features[df_features["city"] == city].sort_values("timestamp")
    # Преобразуем timestamp в числовой формат для регрессии
    city_df = city_df.copy()
    city_df["days_since_start"] = (city_df["timestamp"] - city_df["timestamp"].min()).dt.days
    
    # Простая линейная регрессия для тренда
    x = city_df["days_since_start"].values
    y = city_df["temperature"].values
    coeffs = polyfit(x, y, 1)
    trend_line = poly1d(coeffs)
    
    # Добавляем тренд на график
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=city_df["timestamp"],
        y=city_df["temperature"],
        mode='lines',
        name='Температура',
        line=dict(color='blue', width=1)
    ))
    fig_trend.add_trace(go.Scatter(
        x=city_df["timestamp"],
        y=trend_line(x),
        mode='lines',
        name='Тренд',
        line=dict(color='red', width=2, dash='dash')
    ))
    fig_trend.update_layout(
        title=f"Долгосрочный тренд температуры — {city}",
        xaxis_title="Дата",
        yaxis_title="Температура (°C)",
        hovermode='x unified'
    )
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # Показываем изменение температуры за период
    temp_change = trend_line(x[-1]) - trend_line(x[0])
    years_span = (city_df["timestamp"].max() - city_df["timestamp"].min()).days / 365.25
    st.info(
        f"Тренд: {temp_change:+.2f} °C за весь период "
        f"({years_span:.1f} лет) = {temp_change/years_span:+.3f} °C/год"
    )
    
    # Таблица сезонной статистики (mean/std по сезонам)
    st.subheader("Сезонная статистика")
    city_data = df_features[df_features["city"] == city]
    season_stats = (
        city_data.groupby("season")
        .agg({
            "season_mean": "first",
            "season_std": "first",
            "temperature": ["count", "min", "max"]
        })
        .round(2)
    )
    # Упрощаем MultiIndex колонки
    season_stats.columns = ["_".join(col).strip() if isinstance(col, tuple) else col for col in season_stats.columns]
    # Переименовываем колонки для отображения
    season_stats = season_stats.rename(columns={
        "season_mean_first": "Среднее (°C)",
        "season_std_first": "Ст. отклонение (°C)",
        "temperature_count": "Количество",
        "temperature_min": "Мин (°C)",
        "temperature_max": "Макс (°C)"
    })
    season_stats = season_stats.reindex(["winter", "spring", "summer", "autumn"])
    st.dataframe(season_stats, use_container_width=True)
    
    st.subheader("Детальная статистика по сезону")
    st.dataframe(
        df_features[df_features["city"] == city][
            ["timestamp", "temperature", "season", "season_mean", "season_std", "is_anomaly_season", "is_anomaly_rolling"]
        ].sort_values("timestamp")
    )


if __name__ == "__main__":
    main()

