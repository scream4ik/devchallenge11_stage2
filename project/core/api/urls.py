from rest_framework import routers

from .views import EventViewSet, VersionViewSet


router = routers.DefaultRouter()

router.register(r'event', EventViewSet, base_name='event')
router.register(r'version', VersionViewSet, base_name='version')


urlpatterns = router.urls
