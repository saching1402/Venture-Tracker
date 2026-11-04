"""
Import / export endpoints for the weekly refresh job.

Authorised by either the X-Import-Token header (matches IMPORT_TOKEN env var)
or a signed-in staff user. With IMPORT_TOKEN unset, only staff can use them.
"""
import hmac

from django.conf import settings
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
