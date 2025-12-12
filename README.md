# OpenWeatherMap Streamlit Demo

Пример приложения для анализа исторических температур и проверки текущей погоды через OpenWeatherMap.

## Запуск локально
```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export OWM_API_KEY=your_key  # Windows: set OWM_API_KEY=...
streamlit run app.py
```

## Данные
- В `data/temperature_data.csv` — демо-данные по городам.
- Можно загрузить свой CSV (столбцы: `city`, `timestamp`, `temperature`, `season`).

## Функциональность
- Расчёт скользящего среднего/σ и сезонной статистики.
- Выявление аномалий (по сезонной и rolling-статистике).
- Вызов OpenWeatherMap (sync/async) и проверка, нормальна ли текущая температура для сезона.
- Графики: временной ряд с аномалиями, сезонный boxplot.

## Streamlit Cloud
- Укажите ветку `main` и файл `app.py`.
- API-ключ хранить в Secrets (`OWM_API_KEY`), не коммитить.

