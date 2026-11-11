"""Trends API: the whole tab in one payload, follow / notes, reading-list links, theme refresh, snapshot import/export."""
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.importer.services import _s
from apps.importer.views import ImportTokenOrStaff
from apps.research.models import ResearchJob
from apps.research.views import CanResearch, can_research, model_menu, pick_model

from .engine import queue_theme
from .models import Theme, TrendResource
from .services import add_resource, export_trends, import_trends, resource_json, trends_payload


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trends(request):
    data = trends_payload()
    data.update(can_edit=can_research(request.user), enabled=bool(settings.ANTHROPIC_API_KEY),
                active=ResearchJob.objects.filter(kind='theme', status__in=['queued', 'running']).count(), **model_menu())
    return Response(data)


@api_view(['PATCH'])
@permission_classes([CanResearch])
def theme_update(request, slug):
    t = Theme.objects.filter(slug=slug).first()
    if not t:
        return Response({'detail': 'Unknown theme.'}, status=status.HTTP_404_NOT_FOUND)
    if 'followed' in request.data:
        t.followed = bool(request.data['followed'])
    if 'user_note' in request.data:
        t.user_note = _s(request.data['user_note'])
    t.save()
    return Response({'id': t.slug, 'followed': t.followed, 'user_note': t.user_note})


@api_view(['POST'])
@permission_classes([CanResearch])
def theme_refresh(request, slug):
    t = Theme.objects.filter(slug=slug).first()
    if not t:
        return Response({'detail': 'Unknown theme.'}, status=status.HTTP_404_NOT_FOUND)
    if not settings.ANTHROPIC_API_KEY:
        return Response({'detail': 'Refresh is off. Add ANTHROPIC_API_KEY to the Railway service variables.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    job = queue_theme(t, pick_model(request.data.get('model'), settings.RESEARCH_COMPANY_MODEL), request.user)
    return Response({'queued': 1 if job else 0}, status=status.HTTP_202_ACCEPTED)


@api_view(['POST'])
@permission_classes([CanResearch])
def resource_add(request):
    slug = _s(request.data.get('theme'), 64)
    theme = Theme.objects.filter(slug=slug).first() if slug else None
    if slug and not theme:
        return Response({'detail': 'Unknown theme.'}, status=status.HTTP_404_NOT_FOUND)
    r = add_resource(theme, {**request.data, 'pinned': request.data.get('pinned', True)}, via='user', user=request.user)
    if not r:
        return Response({'detail': 'Give a title and a full https:// link (or it is already on the list).'},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(resource_json(r), status=status.HTTP_201_CREATED)


@api_view(['PATCH', 'DELETE'])
@permission_classes([CanResearch])
def resource_item(request, pk):
    r = TrendResource.objects.filter(id=pk).first()
    if not r:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if request.method == 'DELETE':
        r.hidden = True  # kept so the weekly update does not add it back
        r.save(update_fields=['hidden'])
        return Response(status=status.HTTP_204_NO_CONTENT)
    if 'pinned' in request.data:
        r.pinned = bool(request.data['pinned'])
        r.save(update_fields=['pinned'])
    return Response(resource_json(r))


@api_view(['POST'])
@permission_classes([ImportTokenOrStaff])
def trends_import(request):
    if not isinstance(request.data, dict) or not isinstance(request.data.get('themes'), list):
        return Response({'detail': 'Expected {"themes": [...], "brief": {...}, "resources": [...]}'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(import_trends(request.data, source=_s(request.query_params.get('source'), 40) or 'api'),
                    status=status.HTTP_201_CREATED)


trends_import.cls.throttle_scope = 'import'


@api_view(['GET'])
@permission_classes([ImportTokenOrStaff])
def trends_export(request):
    return Response(export_trends())
