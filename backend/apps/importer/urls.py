from django.urls import path

from .views import export_snapshot, import_snapshot, pipeline_file, upsert_companies_view

urlpatterns = [
    path('import/', import_snapshot, name='import-snapshot'),
    path('export/', export_snapshot, name='export-snapshot'),
    path('import/companies/', upsert_companies_view, name='upsert-companies'),
    path('pipeline/<str:name>', pipeline_file, name='pipeline-file'),
]
