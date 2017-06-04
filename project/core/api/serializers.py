from rest_framework import serializers
from rest_framework.reverse import reverse

from ..models import Event

from reversion.models import Version


class EventSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели Event
    """
    versions = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = '__all__'

    @staticmethod
    def get_versions(obj) -> list:
        versions = Version.objects.get_for_object(obj)
        return [
            reverse('version-detail', args=[v.pk])
            for v in versions
            if obj.description_full != v.field_dict['description_full']
        ]
