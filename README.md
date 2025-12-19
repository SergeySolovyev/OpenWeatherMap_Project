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

### Развертывание

1. Перейдите на [Streamlit Community Cloud](https://streamlit.io/cloud)
2. Войдите через GitHub
3. Нажмите **"New app"**
4. Выберите репозиторий: `SergeySolovyev/OpenWeatherMap_Project`
5. Укажите:
   - **Branch**: `main`
   - **Main file**: `app.py`
6. В разделе **"Secrets"** добавьте:
   ```
   OWM_API_KEY=ваш_ключ_openweathermap
   ```
7. Нажмите **"Deploy!"**

### Ссылка на приложение

🔗 **Приложение**: https://openweathermap-d5mkmcscpxiqemhpeshyq6.streamlit.app/ 



