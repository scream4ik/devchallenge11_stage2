from django.core.management.base import BaseCommand

from ...parser import Dou


class Command(BaseCommand):
    """
    Команда запуска парсера данных календаря событий с сайта https://dou.ua/
    """
    def handle(self, *args, **options):
        dou = Dou()
        dou.start()
