import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import datetime
import asyncio
import aiohttp
import os

CBR_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    clients = set()

    def open(self):
        print("🔌 WebSocket подключен")
        WebSocketHandler.clients.add(self)
        # Отправляем текущие курсы сразу при подключении
        self.send_current_rates()
        # Обновляем счетчик наблюдателей у всех клиентов
        self.update_observer_count()

    def on_close(self):
        print("🔌 WebSocket отключен")
        WebSocketHandler.clients.discard(self)
        # Обновляем счетчик наблюдателей у оставшихся клиентов
        self.update_observer_count()

    def on_message(self, message):
        try:
            data = json.loads(message)
            if data.get('type') == 'ping':
                self.write_message(json.dumps({'type': 'pong'}))
        except:
            pass

    def send_current_rates(self):
        """Отправка текущих курсов клиенту"""
        data = {
            'type': 'currency_rates',
            'rates': currency_rates,
            'timestamp': datetime.datetime.now().isoformat(),
            'observer_count': len(WebSocketHandler.clients)
        }
        try:
            self.write_message(json.dumps(data))
            print(f"📤 Отправлены курсы. Наблюдателей: {len(WebSocketHandler.clients)}")
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")

    def update_observer_count(self):
        """Рассылка обновленного количества наблюдателей всем клиентам"""
        count = len(WebSocketHandler.clients)
        data = {
            'type': 'observer_count',
            'count': count
        }
        for client in WebSocketHandler.clients.copy():
            try:
                client.write_message(json.dumps(data))
            except Exception as e:
                print(f"❌ Ошибка отправки счетчика: {e}")
                WebSocketHandler.clients.discard(client)

    def check_origin(self, origin):
        return True


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/index.html")


# Глобальные курсы валют
currency_rates = {
    'USD': 0.0,
    'EUR': 0.0,
    'GBP': 0.0,
    'CNY': 0.0,
    'JPY': 0.0
}


async def fetch_currency_rates():
    """Получение курсов валют с API ЦБ"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CBR_API_URL) as response:
                if response.status == 200:
                    text = await response.text()
                    data = json.loads(text)

                    rates = {}
                    currencies = ['USD', 'EUR', 'GBP', 'CNY', 'JPY']

                    for currency in currencies:
                        if currency in data.get('Valute', {}):
                            rates[currency] = data['Valute'][currency]['Value']

                    print(f"✅ Получены курсы: {rates}")
                    return rates
                else:
                    print(f"❌ Ошибка API: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None


async def update_rates():
    """Обновление курсов и рассылка клиентам"""
    global currency_rates

    while True:
        print("🔄 Обновление курсов...")
        new_rates = await fetch_currency_rates()

        if new_rates:
            currency_rates.update(new_rates)
            print(f"📊 Новые курсы: {currency_rates}")

            # Рассылаем всем подключенным клиентам
            data = {
                'type': 'currency_rates',
                'rates': currency_rates,
                'timestamp': datetime.datetime.now().isoformat(),
                'observer_count': len(WebSocketHandler.clients)
            }

            for client in WebSocketHandler.clients.copy():
                try:
                    client.write_message(json.dumps(data))
                    print(f"📤 Отправлено клиенту. Всего наблюдателей: {len(WebSocketHandler.clients)}")
                except Exception as e:
                    print(f"❌ Ошибка отправки клиенту: {e}")
                    WebSocketHandler.clients.discard(client)
        else:
            # Тестовые данные если API не доступно
            test_rates = {
                'USD': 75.50,
                'EUR': 80.25,
                'GBP': 95.75,
                'CNY': 10.45,
                'JPY': 0.65
            }
            currency_rates.update(test_rates)
            print(f"📊 Тестовые курсы: {currency_rates}")

            data = {
                'type': 'currency_rates',
                'rates': currency_rates,
                'timestamp': datetime.datetime.now().isoformat(),
                'observer_count': len(WebSocketHandler.clients)
            }

            for client in WebSocketHandler.clients.copy():
                try:
                    client.write_message(json.dumps(data))
                except:
                    WebSocketHandler.clients.discard(client)

        await asyncio.sleep(30)  # Обновление каждые 30 секунд


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/websocket", WebSocketHandler),
    ],
        template_path=os.path.join(os.path.dirname(__file__), ""))


async def main():
    app = make_app()
    app.listen(8888)
    print("🚀 Сервер запущен на http://localhost:8888")

    # Запускаем обновление курсов в фоне
    asyncio.create_task(update_rates())

    # Бесконечный цикл
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())