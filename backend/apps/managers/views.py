from django.db.models import Count
from rest_framework import viewsets
from rest_framework.response import Response

from apps.companies.models import Position
from apps.companies.serializers import HoldingSerializer

from .models import Manager
from .serializers import ManagerDetailSerializer, ManagerListSerializer


class ManagerViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'slug'
    search_fields = ['name', 'hq', 'overview', 'people__name']
    ordering_fields = ['name', 'aum_usd_bn', 'founded']
    ordering = ['-aum_usd_bn']
    filterset_fields = ['type']

    def get_queryset(self):
        return (Manager.objects.prefetch_related('funds', 'people')
                .annotate(n_companies=Count('positions', distinct=True)))

    def get_serializer_class(self):
        return ManagerListSerializer if self.action == 'list' else ManagerDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        mgr = self.get_object()
        data = ManagerDetailSerializer(mgr).data
        holdings = (Position.objects.filter(manager=mgr).select_related('company')
                    .order_by('-company__latest_valuation_usd_bn'))
        data['holdings'] = HoldingSerializer(holdings, many=True).data
        return Response(data)
