from django.urls import path

from .views import export_snapshot, import_snapshot

urlpatterns = [
    path('import/', import_snapshot, name='import-snapshot'),
    path('export/', export_snapshot, name='export-snapshot'),
]
