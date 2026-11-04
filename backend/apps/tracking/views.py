from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.companies.models import Company
from apps.managers.models import Manager

from .models import ChangeEvent, Snapshot, WatchItem


@api_view(['GET'])
def meta(request):
    """Header figures and refresh history."""
    snap = Snapshot.objects.first()
    live = Company.objects.filter(legacy=False, valuation_stale=False)
    consensus = (Company.objects.filter(legacy=False).annotate(n=Count('positions')).filter(n__gte=5).count())
    return Response({
        'asof': snap.asof.isoformat() if snap else None,
        'managers': Manager.objects.filter(is_stub=False).count(),
        'companies': Company.objects.count(),
        'legacy_companies': Company.objects.filter(legacy=True).count(),
        'combined_value_usd_bn': live.aggregate(v=Sum('latest_valuation_usd_bn'))['v'] or 0,
        'combined_aum_usd_bn': Manager.objects.aggregate(v=Sum('aum_usd_bn'))['v'] or 0,
        'consensus_names': consensus,
        'refresh_log': [{'date': s.asof.isoformat(), 'managers': s.managers, 'companies': s.companies,
                         'changes': s.changes_detected, 'source': s.source} for s in Snapshot.objects.all()[:52]],
    })


@api_view(['GET'])
def changes(request):
    qs = ChangeEvent.objects.select_related('company')[:2000]
    return Response([{
        'date': c.date.isoformat(), 'company_id': c.company.slug if c.company else None,
        'company_name': c.company_name, 'type': c.type, 'from': c.from_value, 'to': c.to_value,
        'detail': c.detail,
    } for c in qs])


@api_view(['GET', 'POST'])
def watchlist(request):
    """GET → {managers:[slug], companies:[slug]}; POST {kind, id, on} toggles an item."""
    if request.method == 'POST':
        kind, slug, on = request.data.get('kind'), request.data.get('id'), bool(request.data.get('on', True))
        if kind not in ('manager', 'company') or not slug:
            return Response({'detail': 'kind must be "manager" or "company" and id is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        model = Manager if kind == 'manager' else Company
        obj = model.objects.filter(slug=slug).first()
        if not obj:
            return Response({'detail': f'Unknown {kind}: {slug}'}, status=status.HTTP_404_NOT_FOUND)
        lookup = {'user': request.user, kind: obj}
        if on:
            WatchItem.objects.get_or_create(**lookup)
        else:
            WatchItem.objects.filter(**lookup).delete()
    items = WatchItem.objects.filter(user=request.user).select_related('manager', 'company')
    return Response({
        'managers': [w.manager.slug for w in items if w.manager],
        'companies': [w.company.slug for w in items if w.company],
    })
