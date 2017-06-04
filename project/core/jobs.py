from django_rq import job

from .parser import Dou


@job
def dou_parse_new_events():
    """
    rq команда для обработки новых событий
    """
    dou = Dou()
    dou.start()


@job
def dou_parse_exists_events():
    """
    rq команда для обработки уже существующих в базе данных событий
    """
    dou = Dou()
    dou.start(only_new_events=False)
