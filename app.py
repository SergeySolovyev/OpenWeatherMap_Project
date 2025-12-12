from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from analysis import (
    prepare_features,
    season_from_timestamp,
    current_season_mean_std,
    is_temp_normal,
    load_data,
)
from plots import line_with_anomalies, seasonal_boxplot
from weather_api import fetch_current_weather, fetch_current_weather_async, WeatherError


DATA_PATH = Path(__file__).parent / "data" / "temperature_data.csv"


@st.cache_data
def load_sample_data() -> pd.DataFrame:
    return load_data(str(DATA_PATH))


def main():
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

    df_features = prepare_features(df)
    cities = sorted(df_features["city"].unique())
    city = st.selectbox("Город", cities)

    api_key_input = st.text_input("OpenWeatherMap API key", type="password")
    use_async = st.toggle("Использовать асинхронный запрос", value=False)

    if st.button("Обновить текущую погоду"):
        try:
            if use_async:
                weather = asyncio.run(fetch_current_weather_async(city, api_key_input or None))
            else:
                weather = fetch_current_weather(city, api_key_input or None)
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
            st.error(str(exc))
        except Exception as exc:  # safety net
            st.error(f"Ошибка: {exc}")

    st.subheader("Временной ряд с аномалиями")
    st.plotly_chart(line_with_anomalies(df_features, city), use_container_width=True)

    st.subheader("Сезонное распределение")
    st.plotly_chart(seasonal_boxplot(df_features, city), use_container_width=True)

    st.subheader("Статистика по сезону")
    st.dataframe(
        df_features[df_features["city"] == city][
            ["timestamp", "temperature", "season", "season_mean", "season_std", "is_anomaly_season", "is_anomaly_rolling"]
        ].sort_values("timestamp")
    )


if __name__ == "__main__":
    main()

