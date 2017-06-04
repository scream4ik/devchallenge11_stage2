from django.utils.encoding import force_text
from django.utils.html import escape

from rest_framework import viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from .serializers import EventSerializer
from ..models import Event

from reversion.models import Version
from reversion_compare.helpers import unified_diff, html_diff


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API точка позволяющая просматривать события
    """
    serializer_class = EventSerializer

    def get_queryset(self):
        """
        Фильтруем данные в зависимости от GET параметров
        """
        qs = Event.objects.all()
        if self.request.GET.get('is_archive'):
            qs = qs.filter(is_archive=True)
        elif self.request.GET.get('is_deleted'):
            qs = qs.filter(is_deleted=True)
        return qs


class VersionViewSet(viewsets.ViewSet):
    """
    API точка позволяющая просматривать изменённые строки события
    """
    def get_object(self):
        return get_object_or_404(Version, pk=self.kwargs.get('pk'))

    def retrieve(self, request, *args, **kwargs):
        """
        Формируем словарь с добавленными и удалёнными строками,
        а так же описание в подсвеченными участками, которые были изменены
        """
        version = self.get_object()
        event = Event.objects.get(pk=version.object_id)

        text1 = event.description_full
        text2 = version.field_dict['description_full']

        data = {
            'highlight': html_diff(text1, text2),
            'added': self.get_modified_lines(text1, text2, '+'),
            'deleted': self.get_modified_lines(text1, text2, '-'),
        }
        return Response(data)

    @staticmethod
    def get_modified_lines(value1: str, value2: str, ident: str) -> str:
        """
        Метод определяет какие конкретно строки были добавлены или удалены
        """
        result = []
        value1 = force_text(value1).splitlines()
        value2 = force_text(value2).splitlines()
        diff = unified_diff(value1, value2, n=2)
        diff_text = '\n'.join(diff)
        for line in diff_text.splitlines():
            line = escape(line)
            if line.startswith(ident):
                result.append(line)
        return '\n'.join(result)
