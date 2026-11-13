"""
Import / export endpoints for the weekly refresh job.

Authorised by either the X-Import-Token header (matches IMPORT_TOKEN env var)
or a signed-in staff user. With IMPORT_TOKEN unset, only staff can use them.
"""
import hmac
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .services import ImportRejected, export_payload, import_payload


class ImportTokenOrStaff(BasePermission):
    message = 'Send a valid X-Import-Token header or sign in as staff.'

    def has_permission(self, request, view) -> bool:
        token = settings.IMPORT_TOKEN
        sent = request.headers.get('X-Import-Token', '')
        if token and sent and hmac.compare_digest(token, sent):
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class ImportThrottle(ScopedRateThrottle):
    scope_attr = 'throttle_scope'


@api_view(['POST'])
@permission_classes([ImportTokenOrStaff])
def import_snapshot(request):
    try:
        stats = import_payload(request.data, source=request.query_params.get('source', 'api'),
                               force=request.query_params.get('force') == '1')
    except ImportRejected as e:
        return Response({'detail': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    return Response(stats, status=status.HTTP_201_CREATED)


import_snapshot.cls.throttle_scope = 'import'


@api_view(['GET'])
@permission_classes([ImportTokenOrStaff])
def export_snapshot(request):
    return Response(export_payload())


PIPELINE_FILES = {'merge.py': 'text/x-python', 'SCHEMA.md': 'text/markdown', 'push_snapshot.py': 'text/x-python'}


def _pipeline_dir() -> Path:
    here = Path(settings.BASE_DIR)
    for d in (here / 'pipeline', here.parent / 'pipeline'):   # Docker image / local checkout
        if d.is_dir():
            return d
    raise Http404('Pipeline files are not available on this server.')


@api_view(['GET'])
@permission_classes([ImportTokenOrStaff])
def pipeline_file(request, name):
    """The weekly refresh downloads the current merge script and schema from the site."""
    if name not in PIPELINE_FILES:
        raise Http404('Unknown pipeline file.')
    path = _pipeline_dir() / name
    if not path.exists():
        raise Http404('Pipeline file missing.')
    return FileResponse(open(path, 'rb'), content_type=f'{PIPELINE_FILES[name]}; charset=utf-8')


@api_view(['POST'])
@permission_classes([ImportTokenOrStaff])
def upsert_companies_view(request):
    """Add / update individual companies without a full snapshot: {"companies": [<snapshot company> + optional "profile"]}."""
    from .services import upsert_companies
    if not isinstance(request.data, dict) or not isinstance(request.data.get('companies'), list):
        return Response({'detail': 'Expected {"companies": [...]}'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(upsert_companies(request.data, source=str(request.query_params.get('source') or 'manual')[:64]))
