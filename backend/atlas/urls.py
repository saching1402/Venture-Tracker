"""Venture GP Atlas root URL configuration."""
from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.users.views import ThrottledTokenObtainPairView


def health(request):
    """Railway healthcheck endpoint — always 200, no auth."""
    return JsonResponse({'status': 'ok'})


def spa_index(request):
    """Serve the React app's index.html (assets are served by WhiteNoise from FRONTEND_DIST)."""
    index = settings.FRONTEND_DIST / 'index.html'
    if not index.exists():
        return HttpResponse('Frontend build not found. The API is available under /api/v1/.', status=404)
    resp = FileResponse(open(index, 'rb'), content_type='text/html; charset=utf-8')
    resp['Cache-Control'] = 'no-cache'
    return resp


urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),

    path('api/v1/auth/token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/managers/', include('apps.managers.urls')),
    path('api/v1/companies/', include('apps.companies.urls')),
    path('api/v1/', include('apps.tracking.urls')),
    path('api/v1/', include('apps.importer.urls')),

    path('', spa_index, name='spa'),
]
