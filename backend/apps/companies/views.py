import django_filters
from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes

from apps.importer.views import ImportTokenOrStaff
from rest_framework.response import Response

from .models import Company, Position, ValuationRound
from .serializers import CompanyDetailSerializer, CompanyListSerializer


class CompanyFilter(django_filters.FilterSet):
    manager = django_filters.CharFilter(field_name='positions__manager__slug')
    min_valuation = django_filters.NumberFilter(field_name='latest_valuation_usd_bn', lookup_expr='gte')
    status = django_filters.CharFilter(field_name='status', lookup_expr='istartswith')

    class Meta:
        model = Company
        fields = ['sector', 'legacy', 'manager', 'min_valuation', 'status']


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'slug'
    filterset_class = CompanyFilter
    search_fields = ['name', 'description', 'ceo', 'hq']
    ordering_fields = ['name', 'latest_valuation_usd_bn', 'revenue_usd_bn', 'step_up_x', 'total_raised_usd_bn']
    ordering = ['-latest_valuation_usd_bn']

    def get_queryset(self):
        positions = Prefetch('positions', queryset=Position.objects.select_related('manager'))
        qs = Company.objects.prefetch_related(positions)
        if self.action == 'retrieve':
            qs = qs.prefetch_related('rounds')
        return qs.distinct()

    def get_serializer_class(self):
        return CompanyListSerializer if self.action == 'list' else CompanyDetailSerializer


@api_view(['GET'])
def recent_rounds(request):
    """Priced rounds / tenders on or after ?since=YYYY-MM (default 2025-07), newest first."""
    since = request.query_params.get('since', '2025-07')
    rows = (ValuationRound.objects.filter(date__gte=since).select_related('company')
            .order_by('-date')[:500])
    return Response([{
        'company_id': r.company.slug, 'date': r.date, 'round': r.round,
        'post_money_usd_bn': r.post_money_usd_bn, 'lead': r.lead,
    } for r in rows])


@api_view(['POST'])
@permission_classes([ImportTokenOrStaff])
def investors_merge(request):
    """Merge sourced investor lists: {"companies": [{"id", "investors": [{"name", "lead"?, "round"?, "year"?}], "sources": [url]}]}.
    Tracked GPs become positions; everyone else goes to other_investors. Additive only."""
    from .investors import merge_investors
    if not isinstance(request.data, dict) or not isinstance(request.data.get('companies'), list):
        return Response({'detail': 'Expected {"companies": [...]}'}, status=400)
    return Response(merge_investors(request.data, source=str(request.query_params.get('source') or 'investor sweep')[:64]))
