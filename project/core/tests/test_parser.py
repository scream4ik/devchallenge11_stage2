from django.test import TestCase

from ..models import Event
from ..parser import Dou

from bs4 import BeautifulSoup
import requests
from datetime import date, time


class DouTest(TestCase):
    """
    Тесты методов класса Dou
    """
    def setUp(self):
        self.dou = Dou()

    def test_pagination(self):
        events_count_before = Event.objects.count()
        self.dou.pagination(1, last_page=2)
        events_count_after = Event.objects.count()
        self.assertTrue(events_count_before < events_count_after)

        self.dou.pagination(300)
        self.assertEqual(events_count_after, Event.objects.count())

    def test_check_exists_links(self):
        events_count_before = Event.objects.count()
        self.dou.check_exists_links()
        self.assertEqual(events_count_before, Event.objects.count())

    def test_create_or_update_event(self):
        url = 'https://dou.ua/calendar/15966/'

        response = requests.get(url, headers=self.dou.headers)
        soup = BeautifulSoup(response.text, 'lxml')
        self.dou.create_or_update_event(soup, response.text, url, False)

        event = Event.objects.get(url=url)

        self.assertEqual(event.title, 'Forum One Ukraine 2017')
        self.assertEqual(
            event.description_short,
            'Forum One Ukraine - глобальный форум Украины и Центральной '
            'Европы. Это площадка, которая ежегодно объединяет крупнейших '
            'лидеров мирового и украинского бизнеса. Событие невероятного '
            'масштаба, которое открывает большие горизонты и формирует новое '
            'бизнес-сообщество нашей страны. Здесь налаживаются деловые '
            'связи, создаются бизнес-проекты и вершится будущее украинского '
            'бизнеса!')
        self.assertEqual(event.date_start, date(2017, 9, 30))
        self.assertEqual(event.time_start, time(9, 00))
        self.assertEqual(event.time_end, time(21, 00))
        self.assertEqual(
            event.location, 'Киев, пл. Спортивная, 1, Дворец спорта'
        )
        self.assertEqual(event.cost, 'от 4500 грн')
        self.assertFalse(event.is_archive)

    def test_get_event_date(self):
        html = """
        <div class="event-info-row">
                    <div class="dt">
                            Відбудеться
                    </div>
                    <div class="dd">31 грудня (субота)</div>
                </div>
        """
        date_start, date_end = self.dou.get_event_date(html)
        self.assertEqual(date_start, date(2017, 12, 31))
        self.assertEqual(date_end, None)

        self.assertRaises(ValueError, lambda: self.dou.get_event_date(""""""))
        self.assertRaisesMessage(
            'Дата не найдена', lambda: self.dou.get_event_date("""""")
        )

    def test_get_event_time(self):
        html = """
        <div class="event-info-row">
            <div class="dt">Час</div>
            <div class="dd">13:40 — 18:00</div>
        </div>
        """
        time_start, time_end = self.dou.get_event_time(html)
        self.assertEqual(time_start, time(13, 40))
        self.assertEqual(time_end, time(18, 00))

        time_start, time_end = self.dou.get_event_time("""""")
        self.assertEqual(time_start, None)
        self.assertEqual(time_end, None)

    def test_get_event_location(self):
        html = """
        <div class="event-info-row">
            <div class="dt">Место</div>
            <div class="dd">Киев, пл. Спортивная, 1, Дворец спорта</div>
        </div>
        """
        location = self.dou.get_event_location(html)
        self.assertEqual(
            location, 'Киев, пл. Спортивная, 1, Дворец спорта'
        )

        location = self.dou.get_event_location("""""")
        self.assertEqual(location, '')

    def test_get_event_cost(self):
        html = """
        <div class="event-info-row">
            <div class="dt">Стоимость</div>
            <div class="dd">от 4500 грн</div>
        </div>
        """
        cost = self.dou.get_event_cost(html)
        self.assertEqual(cost, 'от 4500 грн')

        cost = self.dou.get_event_cost("""""")
        self.assertEqual(cost, '')
