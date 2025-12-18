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


def load_data(path) -> pd.DataFrame:
    # Поддерживаем как строки (путь к файлу), так и file-like объекты (file_uploader)
    if isinstance(path, str):
        df = pd.read_csv(path)
    else:
        # Для file_uploader из Streamlit
        df = pd.read_csv(path)
    
    # Сбрасываем индекс для избежания проблем с дублирующимися индексами
    df = df.reset_index(drop=True)
    
    # Убеждаемся, что индексы уникальны
    if not df.index.is_unique:
        df = df.reset_index(drop=True)
    
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if "season" not in df.columns:
        df["season"] = df["timestamp"].apply(season_from_timestamp)
    
    # Финальная проверка уникальности индексов
    if not df.index.is_unique:
        df = df.reset_index(drop=True)
    
    return df


def add_rolling_stats(df: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
    # Создаем полную копию и полностью сбрасываем индекс
    df = df.copy()
    df = df.sort_values(["city", "timestamp"]).reset_index(drop=True)
    
    # Создаем списки для результатов
    rolling_mean_list = []
    rolling_std_list = []
    
    # Вычисляем rolling статистики для каждого города отдельно
    # Это гарантирует правильное выравнивание индексов
    for city in df["city"].unique():
        city_mask = df["city"] == city
        city_df = df[city_mask].copy().reset_index(drop=True)
        
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
        
        # Добавляем в списки
        rolling_mean_list.extend(city_rolling_mean)
        rolling_std_list.extend(city_rolling_std)
    
    # Создаем новый DataFrame с результатами, избегая проблем с индексами
    # Используем pd.DataFrame.assign для безопасного создания колонок
    result_df = df.copy().reset_index(drop=True)
    
    # Создаем Series с правильными индексами
    rolling_mean_series = pd.Series(rolling_mean_list, index=result_df.index, dtype=float)
    rolling_std_series = pd.Series(rolling_std_list, index=result_df.index, dtype=float)
    
    # Используем assign для безопасного добавления колонок
    result_df = result_df.assign(rolling_mean=rolling_mean_series, rolling_std=rolling_std_series)
    
    return result_df


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


