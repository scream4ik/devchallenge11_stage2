from django.db.models import Q
from django.utils import timezone

from .models import Event

import requests
from bs4 import BeautifulSoup
import reversion

import re
from datetime import datetime, date, time
from typing import Tuple, Optional


class Dou:
    """
    Класс для сбора данных событий с сайта https://dou.ua/

    Для обработки новых событий вызвать метод start.

    Для обработки уже существующих событий в базе данных
    вызвать метод start с аргументом only_new_events=False
    """
    calendar_url = 'https://dou.ua/calendar/page-{}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/54.0.2840.71 Safari/537.36',
    }
    event_urls = Event.objects.filter(Q(is_archive=True) | Q(is_deleted=True))\
                              .values_list('url', flat=True)

    def start(self, only_new_events: bool = True, last_page: int = None):
        """
        В зависимости от состояния переменной only_new_events
        проверяем только новые события или уже существующие в нашей базе данных
        """
        if only_new_events:
            self.pagination(1, last_page)
        else:
            self.check_exists_links()

    def pagination(self, page: int, last_page: int = None):
        """
        Проходимся по каждой странице календаря,
        получаем ссылки с новыми событиями и парсим их данные.
        Для перехода на следующую страницу рекурсовно вызываем сами себя.
        Мы можем принудительно указать сколько страниц обрабатывать,
        передав число параметром last_page (в основном для unit тестов)
        """
        response = requests.get(
            self.calendar_url.format(page), headers=self.headers
        )
        # Мы прошли все страницы
        if response.status_code == 404:
            return

        soup = BeautifulSoup(response.text, 'lxml')

        for link in soup.select('.b-postcard .title a'):
            # Мы хотим просканировать только новые (которых у нас нет) события.
            # Остальные сканируются с другой переодичностью
            if link.get('href') in self.event_urls:
                continue

            response = requests.get(link.get('href'), headers=self.headers)
            soup = BeautifulSoup(response.text, 'lxml')

            self.create_or_update_event(soup, response.text, link.get('href'))

        if last_page == page:
            return

        self.pagination(page + 1)

    def check_exists_links(self):
        """
        Повторно проходимя по уже существующим у нас событиям
        и обновляем данные по ним
        """
        for url in self.event_urls:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'lxml')

            is_deleted = False
            # Событие могли удалить. Нам нужно пометить это
            if response.status_code == 404:
                is_deleted = True

            self.create_or_update_event(soup, response.text, url, is_deleted)

    def create_or_update_event(
            self,
            soup: BeautifulSoup,
            text: str,
            link: str,
            is_deleted: bool = False
    ):
        """
        Создаём или обновляем событие.
        Зависит от того, или уже в нашей базе есть урл данного события
        """
        with reversion.create_revision():
            try:
                event = Event.objects.get(url=link)
            except Event.DoesNotExist:
                event = Event(url=link)

            date_start, date_end = self.get_event_date(text)
            time_start, time_end = self.get_event_time(text)

            if not is_deleted:
                event.title = soup.select_one('.page-head h1').string
                event.description_short = soup.select_one('meta[name=description]')['content']
                event.description_full = str(soup.select_one('.b-typo'))
                event.description_full_striptags = soup.select_one('.b-typo').text
                event.date_start = date_start
                # Не обязательные поля
                event.date_end = date_end
                event.time_start = time_start
                event.time_end = time_end
                event.location = self.get_event_location(text)
                event.cost = self.get_event_cost(text)

            # Событие уже прошло. Пометим
            if timezone.now().date() > event.date_start:
                event.is_archive = True

            event.is_deleted = is_deleted
            event.save()

    @staticmethod
    def get_event_date(string: str) -> Tuple[date, Optional[date]]:
        """
        Метод принимает содержимое страницы,
        находит дату начала и окончания ивента
        и возвращает эти данные в виде date объектов
        """
        search = re.search(
            r'<div class="dt">\s*[пройдет|date|відбудеться]+\s*</div>\s*<div class="dd">(\d{1,2})\s?[-|—]?\s?(\d{1,2})?\s([а-я|a-z]+)\s?.*</div>',
            string.lower(),
            flags=re.I + re.U
        )
        if search is None:
            raise ValueError('Дата не найдена')

        event_start_day = search.group(1)
        event_end_day = search.group(2)
        event_month = search.group(3)
        event_year = datetime.now().year
        current_month = datetime.now().month

        # Месяцы могут быть указаны на русском, английском и украинском
        months = {
            'января': 1, 'февраля': 2, 'марта': 3,
            'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
            'january': 1, 'february': 2, 'march': 3,
            'april': 4, 'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4, 'травня': 5,
            'червня': 6, 'липня': 7, 'серпня': 8, 'вересня': 9, 'жовтня': 10,
            'листопада': 11, 'грудня': 12,
        }

        # Если текущий месяц больше месяца события, значит событие
        # произойдёт в следующем году
        if current_month > months.get(event_month):
            event_year += 1

        date_start = date(
            event_year, months.get(event_month), int(event_start_day)
        )

        # Не у всех событий есть дата окончания
        if event_end_day is not None:
            date_end = date(
                event_year, months.get(event_month), int(event_end_day)
            )
        else:
            date_end = None

        return date_start, date_end

    @staticmethod
    def get_event_time(string: str) -> Tuple[Optional[time], Optional[time]]:
        """
        Метод принимает содержимое страницы,
        находит время начала и окончания ивента
        и возвращает эти данные в виде time объектов
        """
        search = re.search(
            r'<div class="dt">\s*[Время|Time|Початок|Час]+\s*</div>\s*<div class="dd">(\d{1,2}:\d{1,2})\s?[-|—]?\s?(\d{1,2}:\d{1,2})?</div>',
            string,
            flags=re.I + re.U
        )
        # Не у всех событий есть время окончания
        if search is None:
            return None, None

        time_start, time_end = search.group(1), search.group(2)
        time_start = datetime.strptime(time_start, '%H:%M').time()

        if time_end is not None:
            time_end = datetime.strptime(time_end, '%H:%M').time()

        return time_start, time_end

    @staticmethod
    def get_event_location(string: str) -> str:
        """
        Метод принимает содержимое страницы,
        находит место проведения и возвращает его
        """
        search = re.search(
            r'<div class="dt">\s*[Место|Place|Місце]+\s*</div>\s*<div class="dd">(.+)</div>',
            string,
            flags=re.I + re.U
        )
        # Не у всех событий есть время окончания
        if search is None:
            return ''

        return search.group(1)

    @staticmethod
    def get_event_cost(string: str) -> str:
        """
        Метод принимает содержимое страницы,
        находит стоимость проведения и возвращает его
        """
        search = re.search(
            r'<div class="dt">\s*[Стоимость|Price|Вартість]+\s*</div>\s*<div class="dd">(.+)</div>',
            string,
            flags=re.I + re.U
        )
        # Не у всех событий есть стоимость
        if search is None:
            return ''

        return search.group(1)
