from django.contrib import admin

from .models import Event

from reversion_compare.admin import CompareVersionAdmin


@admin.register(Event)
class EventAdmin(CompareVersionAdmin):
    pass
