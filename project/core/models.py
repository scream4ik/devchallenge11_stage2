from django.db import models

from reversion import revisions as reversion


@reversion.register
class Event(models.Model):
    """
    Модель событий
    """
    title = models.CharField('название', max_length=250)
    description_short = models.TextField('краткое описание')
    description_full = models.TextField('полное описание')
    description_full_striptags = models.TextField(
        'полное описание',
        help_text='без html тегов'
    )
    date_start = models.DateField('дата начала')
    date_end = models.DateField('дата окончания', blank=True, null=True)
    time_start = models.TimeField('время начала', blank=True, null=True)
    time_end = models.TimeField('время окончания', blank=True, null=True)
    location = models.CharField('место проведения', max_length=200, blank=True)
    cost = models.CharField('стоимость', max_length=200, blank=True)
    url = models.URLField('ссылка', unique=True)
    is_archive = models.BooleanField('в архиве', default=False)
    is_deleted = models.BooleanField('удалено', default=False)

    class Meta:
        verbose_name = 'событие'
        verbose_name_plural = 'события'
        ordering = ('date_start',)

    def __str__(self):
        return self.title
