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
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if "season" not in df.columns:
        df["season"] = df["timestamp"].apply(season_from_timestamp)
    return df


def add_rolling_stats(df: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
    df = df.sort_values(["city", "timestamp"]).copy()
    # Сохраняем исходный индекс для последующего выравнивания
    original_index = df.index.copy()
    df = df.reset_index(drop=True)
    
    # Вычисляем rolling статистики
    rolling_mean = (
        df.groupby("city")
        .rolling(window=window_days, on="timestamp")["temperature"]
        .mean()
        .reset_index(level=0, drop=True)
    )
    rolling_std = (
        df.groupby("city")
        .rolling(window=window_days, on="timestamp")["temperature"]
        .std()
        .reset_index(level=0, drop=True)
    )
    
    # Присваиваем значения через .values для избежания проблем с индексами
    # Индексы должны совпадать, так как мы сбросили индекс перед rolling
    df["rolling_mean"] = rolling_mean.values
    df["rolling_std"] = rolling_std.values
    
    # Восстанавливаем исходный индекс если нужно (но обычно не требуется)
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


