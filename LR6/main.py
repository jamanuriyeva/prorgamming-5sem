import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import datetime
import asyncio
from typing import List, Dict, Any
import aiohttp
import os

# API ЦБ РФ для получения курсов валют
CBR_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"


class CurrencyObserver:
    """Интерфейс наблюдателя"""

    def update(self, currency_data: Dict[str, Any]):
        raise NotImplementedError()


class CurrencySubject:
    """Субъект (Subject) для управления наблюдателями и курсами валют"""

    def __init__(self):
        self._observers: List[CurrencyObserver] = []
        self._previous_rates = {}
        self._current_rates = {}

    def add_observer(self, observer: CurrencyObserver) -> None:
        """Добавление наблюдателя"""
        if observer not in self._observers:
            self._observers.append(observer)
            print(f"Добавлен новый наблюдатель. Всего наблюдателей: {len(self._observers)}")

    def remove_observer(self, observer: CurrencyObserver):
        """Удаление наблюдателя"""
        if observer in self._observers:
            self._observers.remove(observer)
            print(f"Удален наблюдатель. Всего наблюдателей: {len(self._observers)}")

    def notify_observers(self):
        """Уведомление всех наблюдателей"""
        currency_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'rates': self._current_rates,
            'previous_rates': self._previous_rates,
            'changes': self._get_rate_changes()
        }

        for observer in self._observers:
            try:
                observer.update(currency_data)
            except Exception as e:
                print(f"Ошибка при уведомлении наблюдателя: {e}")

    def _get_rate_changes(self) -> Dict[str, Dict[str, float]]:
        """Вычисление изменений курсов"""
        changes = {}
        for currency, current_rate in self._current_rates.items():
            previous_rate = self._previous_rates.get(currency)
            if previous_rate:
                change = current_rate - previous_rate
                change_percent = (change / previous_rate) * 100
                changes[currency] = {
                    'absolute': round(change, 4),
                    'percent': round(change_percent, 2)
                }
        return changes

    def update_rates(self, new_rates: Dict[str, float]):
        """Обновление курсов валют"""
        self._previous_rates = self._current_rates.copy()
        self._current_rates = new_rates

        # Уведомляем наблюдателей только если есть изменения
        if self._previous_rates != self._current_rates:
            print(f"Обнаружены изменения курсов. Уведомляем {len(self._observers)} наблюдателей")
            self.notify_observers()


class WebSocketObserver(CurrencyObserver, tornado.websocket.WebSocketHandler):
    """Наблюдатель, реализованный как WebSocket соединение"""

    observer_id_counter = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        WebSocketObserver.observer_id_counter += 1
        self.observer_id = WebSocketObserver.observer_id_counter

    def update(self, currency_data: Dict[str, Any]):
        """Обновление данных для WebSocket клиента"""
        try:
            message = {
                'type': 'currency_update',
                'observer_id': self.observer_id,
                'data': currency_data
            }
            self.write_message(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            print(f"Ошибка отправки сообщения наблюдателю {self.observer_id}: {e}")

    def open(self):
        """При открытии WebSocket соединения"""
        print(f"WebSocket соединение открыто. ID наблюдателя: {self.observer_id}")
        currency_subject.add_observer(self)

        # Отправляем приветственное сообщение
        welcome_message = {
            'type': 'welcome',
            'observer_id': self.observer_id,
            'message': f'Вы подключены как наблюдатель #{self.observer_id}',
            'current_rates': currency_subject.get_current_rates()
        }
        self.write_message(json.dumps(welcome_message, ensure_ascii=False))

    def on_close(self):
        """При закрытии WebSocket соединения"""
        print(f"WebSocket соединение закрыто. ID наблюдателя: {self.observer_id}")
        currency_subject.remove_observer(self)

    def on_message(self, message):
        """Обработка входящих сообщений"""
        try:
            data = json.loads(message)
            if data.get('type') == 'ping':
                self.write_message(json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            print(f"Неверный JSON от наблюдателя {self.observer_id}")

    def check_origin(self, origin):
        """Разрешаем кросс-доменные запросы"""
        return True


class MainHandler(tornado.web.RequestHandler):
    """Главная страница"""

    def get(self):
        self.render("index.html")


class CurrencyFetcher:
    """Класс для получения данных о курсах валют с API ЦБ РФ"""

    def __init__(self, subject: CurrencySubject):
        self.subject = subject

    async def fetch_currency_rates(self):
        """Получение курсов валют с API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(CBR_API_URL) as response:
                    if response.status == 200:
                        # Получаем текст и парсим JSON вручную
                        text = await response.text()
                        data = json.loads(text)
                        return self._parse_currency_data(data)
                    else:
                        print(f"Ошибка при запросе к API: {response.status}")
                        return None
        except Exception as e:
            print(f"Ошибка при получении данных о валютах: {e}")
            return None

    def _parse_currency_data(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Парсинг данных о валютах"""
        rates = {}

        # Основные валюты для отслеживания
        target_currencies = {
            'USD': 'Доллар США',
            'EUR': 'Евро',
            'GBP': 'Британский фунт',
            'CNY': 'Китайский юань',
            'JPY': 'Японская иена'
        }

        for currency_code, currency_name in target_currencies.items():
            if currency_code in data['Valute']:
                currency_data = data['Valute'][currency_code]
                rates[currency_code] = currency_data['Value']

        return rates

    async def start_monitoring(self, interval: int = 60) -> None:
        """Запуск мониторинга курсов валют"""
        while True:
            print(f"Запрос курсов валют... {datetime.datetime.now()}")
            new_rates = await self.fetch_currency_rates()

            if new_rates:
                self.subject.update_rates(new_rates)

                # Логируем текущие курсы
                print("Текущие курсы валют:")
                for currency, rate in new_rates.items():
                    print(f"  {currency}: {rate} руб.")
            else:
                print("Не удалось получить данные о курсах валют")
                # Используем тестовые данные для демонстрации
                test_rates = {
                    'USD': 75.50 + (datetime.datetime.now().minute % 10) * 0.1,
                    'EUR': 80.25 + (datetime.datetime.now().minute % 10) * 0.1,
                    'GBP': 95.75 + (datetime.datetime.now().minute % 10) * 0.1,
                    'CNY': 10.45 + (datetime.datetime.now().minute % 10) * 0.1,
                    'JPY': 0.65 + (datetime.datetime.now().minute % 10) * 0.01
                }
                self.subject.update_rates(test_rates)
                print("Используются тестовые данные для демонстрации")

            await asyncio.sleep(interval)


# Глобальный экземпляр субъекта
currency_subject = CurrencySubject()


def make_app():
    """Создание Tornado приложения"""
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/websocket", WebSocketObserver),
    ],
        template_path="templates" if os.path.exists("templates") else "."
    )


async def main():
    """Основная функция"""
    # Создание приложения
    app = make_app()
    app.listen(8888)
    print("Сервер запущен на http://localhost:8888")

    # Запуск мониторинга курсов валют
    fetcher = CurrencyFetcher(currency_subject)

    # Запускаем мониторинг в фоновой задаче
    asyncio.create_task(fetcher.start_monitoring(interval=30))  # Обновление каждые 30 секунд

    # Бесконечный цикл для поддержания работы приложения
    await asyncio.Event().wait()


if __name__ == "__main__":
    import os

    asyncio.run(main())