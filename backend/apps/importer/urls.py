from django.urls import path

from .views import export_snapshot, import_snapshot, pipeline_file

urlpatterns = [
    path('import/', import_snapshot, name='import-snapshot'),
    path('export/', export_snapshot, name='export-snapshot'),
    path('pipeline/<str:name>', pipeline_file, name='pipeline-file'),
]
