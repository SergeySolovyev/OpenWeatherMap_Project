from __future__ import annotations

import pandas as pd
import numpy as np

MONTH_TO_SEASON = {
    12: "winter",
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
}


def season_from_timestamp(ts: pd.Timestamp) -> str:
    return MONTH_TO_SEASON[ts.month]


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Сбрасываем индекс для избежания проблем с дублирующимися индексами
    df = df.reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if "season" not in df.columns:
        df["season"] = df["timestamp"].apply(season_from_timestamp)
    return df


def add_rolling_stats(df: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
    # Создаем полную копию и сбрасываем индекс для избежания проблем
    df = df.copy()
    df = df.sort_values(["city", "timestamp"]).reset_index(drop=True)
    
    # Убеждаемся, что индексы уникальны
    if not df.index.is_unique:
        df = df.reset_index(drop=True)
    
    # Инициализируем колонки с NaN значениями
    df["rolling_mean"] = np.nan
    df["rolling_std"] = np.nan
    
    # Вычисляем rolling статистики для каждого города отдельно
    # Это гарантирует правильное выравнивание индексов
    for city in df["city"].unique():
        city_mask = df["city"] == city
        city_indices = df[city_mask].index
        
        # Создаем отдельный DataFrame для города
        city_df = df.loc[city_indices].copy().reset_index(drop=True)
        
        # Вычисляем rolling статистики для города
        city_rolling_mean = (
            city_df.rolling(window=window_days, on="timestamp")["temperature"]
            .mean()
            .values
        )
        city_rolling_std = (
            city_df.rolling(window=window_days, on="timestamp")["temperature"]
            .std()
            .values
        )
        
        # Присваиваем значения напрямую по индексам
        df.loc[city_indices, "rolling_mean"] = city_rolling_mean
        df.loc[city_indices, "rolling_std"] = city_rolling_std
    
    return df


def add_season_stats(df: pd.DataFrame) -> pd.DataFrame:
    season_stats = (
        df.groupby(["city", "season"])["temperature"]
        .agg(season_mean="mean", season_std="std")
        .reset_index()
    )
    return df.merge(season_stats, on=["city", "season"], how="left")


def mark_anomalies(
    df: pd.DataFrame, z_threshold: float = 2.0, use_rolling: bool = True
) -> pd.DataFrame:
    df = df.copy()
    df["is_anomaly_season"] = (
        (df["temperature"] > df["season_mean"] + z_threshold * df["season_std"])
        | (df["temperature"] < df["season_mean"] - z_threshold * df["season_std"])
    )
    if use_rolling:
        df["is_anomaly_rolling"] = (
            (df["temperature"] > df["rolling_mean"] + z_threshold * df["rolling_std"])
            | (df["temperature"] < df["rolling_mean"] - z_threshold * df["rolling_std"])
        )
    else:
        df["is_anomaly_rolling"] = False
    return df


def prepare_features(df: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
    """Подготавливает признаки для анализа температурных данных.
    
    ВЫВОД из экспериментов: используется последовательная обработка, а не параллельная.
    ThreadPoolExecutor не эффективен для CPU-bound задач (rolling, вычисления) из-за GIL.
    Накладные расходы на создание потоков превышают выгоду от параллелизма.
    См. experiments.ipynb для детального анализа параллелизации.
    """
    with_rolling = add_rolling_stats(df, window_days=window_days)
    with_season = add_season_stats(with_rolling)
    return mark_anomalies(with_season)


def current_season_mean_std(df: pd.DataFrame, city: str, season: str) -> tuple[float, float]:
    subset = df[(df["city"] == city) & (df["season"] == season)]
    if subset.empty:
        return np.nan, np.nan
    return subset["season_mean"].iloc[0], subset["season_std"].iloc[0]


def is_temp_normal(temp: float, mean: float, std: float, z_threshold: float = 2.0) -> bool:
    if np.isnan(mean) or np.isnan(std) or std == 0:
        return True
    return (mean - z_threshold * std) <= temp <= (mean + z_threshold * std)


