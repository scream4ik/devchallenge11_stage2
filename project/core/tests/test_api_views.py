from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from ..models import Event
from ..parser import Dou

from bs4 import BeautifulSoup
import requests
import reversion

from reversion.models import Version


class EventViewSetTest(APITestCase):
    """
    Тестирование представления EventViewSet
    """
    def setUp(self):
        self.dou = Dou()
        self.dou.start(last_page=1)

    def test_list(self):
        response = self.client.get(reverse('event-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Event.objects.count())

        fields = ('id', 'versions', 'title', 'description_short',
                  'description_full', 'description_full_striptags',
                  'date_start', 'date_end', 'time_start', 'time_end',
                  'location', 'cost', 'url', 'is_archive', 'is_deleted')
        self.assertEqual(
            tuple(next(iter(response.data)).keys()), fields
        )

        response = self.client.get(
            '{}?is_archive=true'.format(reverse('event-list'))
        )
        self.assertEqual(
            len(response.data), Event.objects.filter(is_archive=True).count()
        )

        response = self.client.get(
            '{}?is_deleted=true'.format(reverse('event-list'))
        )
        self.assertEqual(
            len(response.data), Event.objects.filter(is_deleted=True).count()
        )


class VersionViewSetTest(APITestCase):
    """
    Тестирование представления VersionViewSet
    """
    def setUp(self):
        self.dou = Dou()

    def test_retrieve(self):
        url = 'https://dou.ua/calendar/15966/'
        response = requests.get(url, headers=self.dou.headers)
        soup = BeautifulSoup(response.text, 'lxml')
        self.dou.create_or_update_event(soup, response.text, url, False)

        with reversion.create_revision():
            event = Event.objects.get(url=url)
            event.description_full = 'another event description'
            event.save()

        version = Version.objects.filter(object_id=event.pk).last()
        response = self.client.get(
            reverse('version-detail', args=[version.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        fields = ('deleted', 'added', 'highlight')
        self.assertTrue(all([x in response.data.keys() for x in fields]))
