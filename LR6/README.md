
# Реализация паттерна «Наблюдатель» для отслеживания курсов валют ЦБ РФ

## Цель работы
Целью работы является создание приложения на Python, реализующего паттерн проектирования **«Наблюдатель»** для отслеживания изменений курсов валют, предоставляемых **API Центробанка РФ**, и рассылки обновлений подключённым клиентам через **WebSocket** в реальном времени.

---

## Запуск проекта

### 1. Установка зависимостей
```bash
pip install tornado aiohttp
````

### 2. Запуск сервера

```bash
python app.py
```

### 3. Открытие клиента

Перейдите в браузере:

```
http://localhost:8888/
```

---

## Как проверить работу (имитация обновлений)

Сервер запрашивает новые курсы **каждые 30 секунд** (`interval=30`).
Чтобы имитировать обновления раз в 5 минут, измените:

```python
asyncio.create_task(fetcher.start_monitoring(interval=300))
```

---

## Скриншоты
![](https://github.com/jamanuriyeva/prorgamming-5sem/blob/5cf52fed411f6cbcc355093e00c766c0cb4f0d66/LR6/pics/1.png)

![](https://github.com/jamanuriyeva/prorgamming-5sem/blob/5cf52fed411f6cbcc355093e00c766c0cb4f0d66/LR6/pics/2.png)

![](https://github.com/jamanuriyeva/prorgamming-5sem/blob/5cf52fed411f6cbcc355093e00c766c0cb4f0d66/LR6/pics/3.png)
