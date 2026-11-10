"""Shortlist API: list / add / edit / remove, priority changes (logged), refresh one or all, dismiss news."""
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.companies.models import Company
from apps.importer.services import _f, _s
from apps.managers.models import Manager
from apps.research.engine import find_company, find_manager, unique_slug
from apps.research.models import ResearchJob
from apps.research.views import CanResearch, can_research, model_menu, pick_model

from .engine import link_target, queue_refresh
from .models import NewsItem, PriorityChange, ShortlistItem

LEVELS = ('L1', 'L2', 'L3')


def _who(user) -> str:
    return getattr(user, 'full_name', '') or getattr(user, 'email', '') or 'Unknown'


def _iso(d):
    return d.isoformat() if d else None


def _company_json(co: Company | None) -> dict | None:
    if not co:
        return None
    return {
        'id': co.slug, 'name': co.name, 'website': co.website, 'hq': co.hq, 'sector': co.sector, 'description': co.description,
        'status': co.status, 'latest_valuation_usd_bn': co.latest_valuation_usd_bn, 'valuation_date': co.valuation_date,
        'valuation_label': co.valuation_label, 'valuation_basis': co.valuation_basis, 'total_raised_usd_bn': co.total_raised_usd_bn,
        'revenue_metric': co.revenue_metric, 'revenue_usd_bn': co.revenue_usd_bn, 'revenue_date': co.revenue_date,
        'revenue_label': co.revenue_label, 'growth': co.growth, 'profitability': co.profitability,
        'step_up_x': co.step_up_x, 'ev_rev_x': co.ev_rev_x, 'research_status': co.research_status,
        'rounds': [{'date': r.date, 'round': r.round, 'post_money_usd_bn': r.post_money_usd_bn, 'lead': r.lead} for r in co.rounds.all()],
        'tracked_gp_ids': [p.manager.slug for p in co.positions.all()],
    }


def _manager_json(m: Manager | None) -> dict | None:
    if not m:
        return None
    return {
        'id': m.slug, 'name': m.name, 'website': m.website, 'hq': m.hq, 'type': m.type, 'overview': m.overview,
        'aum_usd_bn': m.aum_usd_bn, 'aum_date': m.aum_date, 'aum_label': m.aum_label, 'stages': m.stages,
        'focus_areas': m.focus_areas, 'performance': m.performance, 'performance_label': m.performance_label,
        'research_status': m.research_status,
        'funds': [{'name': f.name, 'size_usd_bn': f.size_usd_bn, 'vintage': f.vintage, 'label': f.label} for f in m.funds.all()],
    }


def item_json(i: ShortlistItem) -> dict:
    return {
        'id': i.id, 'kind': i.kind, 'name': i.name,
        'my_priority': i.my_priority, 'my_priority_since': _iso(i.my_priority_since),
        'claude_priority': i.claude_priority, 'claude_priority_since': _iso(i.claude_priority_since),
        'claude_rationale': i.claude_rationale,
        'thesis': i.thesis, 'rounds_plan': i.rounds_plan, 'target_allocation_usd_m': i.target_allocation_usd_m,
        'brief': i.brief, 'momentum': i.momentum, 'performance': i.performance, 'next_round': i.next_round,
        'catalysts': i.catalysts, 'risks': i.risks, 'sources': i.sources,
        'research_status': i.research_status, 'last_refreshed_at': _iso(i.last_refreshed_at), 'last_error': i.last_error,
        'added_at': _iso(i.added_at), 'added_by': _who(i.added_by) if i.added_by_id else '',
        'company': _company_json(i.company), 'manager': _manager_json(i.manager),
        'news': [{'id': n.id, 'date': n.date, 'headline': n.headline, 'summary': n.summary, 'category': n.category,
                  'importance': n.importance, 'source': n.source, 'url': n.url, 'found_at': _iso(n.found_at)}
                 for n in [n for n in i.news.all() if not n.hidden][:80]],
        'priority_log': [{'id': p.id, 'track': p.track, 'old': p.old, 'new': p.new, 'note': p.note,
                          'changed_by': p.changed_by, 'changed_at': _iso(p.changed_at)} for p in i.priority_log.all()],
        'marks': [{'as_of': _iso(m.as_of), 'valuation_usd_bn': m.valuation_usd_bn, 'valuation_date': m.valuation_date,
                   'revenue_usd_bn': m.revenue_usd_bn, 'revenue_metric': m.revenue_metric, 'revenue_date': m.revenue_date,
                   'aum_usd_bn': m.aum_usd_bn, 'note': m.note} for m in list(i.marks.all())[:40]],
    }


def _items():
    return (ShortlistItem.objects.select_related('company', 'manager', 'added_by')
            .prefetch_related('company__rounds', 'company__positions__manager', 'manager__funds',
                              'news', 'priority_log', 'marks'))


def _one(pk: int) -> ShortlistItem | None:
    return _items().filter(id=pk).first()


def _level(v) -> str | None:
    """'' clears; None means invalid."""
    v = str(v or '').strip().upper()
    return v if v in LEVELS or v == '' else None


def set_my_priority(item: ShortlistItem, level: str, note: str, who: str) -> bool:
    if level == item.my_priority:
        return False
    PriorityChange.objects.create(item=item, track='mine', old=item.my_priority, new=level, note=note[:2000], changed_by=who)
    item.my_priority, item.my_priority_since = level, (timezone.now() if level else None)
    return True


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def shortlist(request):
    if request.method == 'GET':
        items = list(_items())
        loose = [i for i in items if (i.kind == 'company' and not i.company_id) or (i.kind == 'fund' and not i.manager_id)]
        for i in loose:
            link_target(i)
        if loose:
            items = list(_items())
        active = ResearchJob.objects.filter(kind='shortlist', status__in=['queued', 'running']).count()
        return Response({'items': [item_json(i) for i in items], 'can_edit': can_research(request.user),
                         'enabled': bool(settings.ANTHROPIC_API_KEY), 'active': active, **model_menu()})

    if not can_research(request.user):
        return Response({'detail': CanResearch.message}, status=status.HTTP_403_FORBIDDEN)
    d = request.data
    kind = 'fund' if d.get('kind') in ('fund', 'manager') else 'company'
    ref = _s(d.get('id'), 96)
    name = _s(d.get('name'), 255)
    website = _s(d.get('website'), 500)
    level = _level(d.get('my_priority'))
    if level is None:
        return Response({'detail': 'Priority must be L1, L2 or L3.'}, status=status.HTTP_400_BAD_REQUEST)
    if not ref and not name:
        return Response({'detail': 'Pick a company / fund or type a name.'}, status=status.HTTP_400_BAD_REQUEST)

    profile_job = None
    if kind == 'company':
        target = Company.objects.filter(slug=ref).first() if ref else find_company(name, website)
        if ref and not target:
            return Response({'detail': f'Unknown company: {ref}'}, status=status.HTTP_404_NOT_FOUND)
        if target and ShortlistItem.objects.filter(company=target).exists():
            return Response({'detail': f'{target.name} is already shortlisted.'}, status=status.HTTP_409_CONFLICT)
        if not target and settings.ANTHROPIC_API_KEY:
            target = Company.objects.create(slug=unique_slug(Company, name, 96), name=name, website=website,
                                            added_via='user', research_status='queued')
            profile_job = ResearchJob.objects.create(kind='company', name=name, website=website, slug=target.slug,
                                                     model=pick_model(d.get('model'), settings.RESEARCH_COMPANY_MODEL),
                                                     created_by=request.user)
    else:
        target = Manager.objects.filter(slug=ref).first() if ref else find_manager(name)
        if ref and not target:
            return Response({'detail': f'Unknown manager: {ref}'}, status=status.HTTP_404_NOT_FOUND)
        if target and ShortlistItem.objects.filter(manager=target).exists():
            return Response({'detail': f'{target.name} is already shortlisted.'}, status=status.HTTP_409_CONFLICT)
        if not target and settings.ANTHROPIC_API_KEY:
            target = Manager.objects.create(slug=unique_slug(Manager, name, 64), name=name, website=website,
                                            added_via='user', is_stub=True, research_status='queued')
            profile_job = ResearchJob.objects.create(kind='manager', name=name, website=website, slug=target.slug,
                                                     model=pick_model(d.get('model'), settings.RESEARCH_MODEL),
                                                     created_by=request.user)
    try:
        item = ShortlistItem.objects.create(
            kind=kind, name=target.name if target else name, added_by=request.user,
            company=target if kind == 'company' else None, manager=target if kind == 'fund' else None,
            thesis=_s(d.get('thesis')), rounds_plan=_s(d.get('rounds_plan')),
            target_allocation_usd_m=_f(d.get('target_allocation_usd_m')))
    except IntegrityError:
        return Response({'detail': 'Already shortlisted.'}, status=status.HTTP_409_CONFLICT)
    if level:
        set_my_priority(item, level, _s(d.get('note')) or 'Added to shortlist', _who(request.user))
        item.save()
    if not profile_job and d.get('refresh', True) and settings.ANTHROPIC_API_KEY:
        queue_refresh(item, pick_model(d.get('model'), settings.RESEARCH_COMPANY_MODEL), request.user)
    return Response(item_json(_one(item.id)), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def shortlist_item(request, pk: int):
    item = _one(pk)
    if not item:
        return Response({'detail': 'Not on the shortlist.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(item_json(item))
    if not can_research(request.user):
        return Response({'detail': CanResearch.message}, status=status.HTTP_403_FORBIDDEN)
    if request.method == 'DELETE':
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    d = request.data
    if 'my_priority' in d:
        level = _level(d.get('my_priority'))
        if level is None:
            return Response({'detail': 'Priority must be L1, L2 or L3.'}, status=status.HTTP_400_BAD_REQUEST)
        set_my_priority(item, level, _s(d.get('note')), _who(request.user))
    for fld in ('thesis', 'rounds_plan'):
        if fld in d:
            setattr(item, fld, _s(d.get(fld)))
    if 'target_allocation_usd_m' in d:
        item.target_allocation_usd_m = _f(d.get('target_allocation_usd_m'))
    item.save()
    return Response(item_json(_one(pk)))


@api_view(['POST'])
@permission_classes([CanResearch])
def refresh_item(request, pk: int):
    item = ShortlistItem.objects.filter(id=pk).first()
    if not item:
        return Response({'detail': 'Not on the shortlist.'}, status=status.HTTP_404_NOT_FOUND)
    if not settings.ANTHROPIC_API_KEY:
        return Response({'detail': 'Refresh is off. Add ANTHROPIC_API_KEY to the Railway service variables.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    job = queue_refresh(item, pick_model(request.data.get('model'), settings.RESEARCH_COMPANY_MODEL), request.user)
    return Response({'queued': 1 if job else 0, 'detail': 'Refresh started.' if job else 'Already refreshing.'},
                    status=status.HTTP_202_ACCEPTED)


@api_view(['POST'])
@permission_classes([CanResearch])
def refresh_all(request):
    """Refresh every item, or a subset: kind=company|fund, priority=L1 (either track), ids=[...]."""
    if not settings.ANTHROPIC_API_KEY:
        return Response({'detail': 'Refresh is off. Add ANTHROPIC_API_KEY to the Railway service variables.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    qs = ShortlistItem.objects.all()
    d = request.data
    if d.get('kind') in ('company', 'fund'):
        qs = qs.filter(kind=d['kind'])
    if d.get('ids'):
        qs = qs.filter(id__in=[int(x) for x in d['ids'] if str(x).isdigit()])
    levels = [lv for lv in (d.get('priority') or []) if lv in LEVELS] if isinstance(d.get('priority'), list) else (
        [d['priority']] if d.get('priority') in LEVELS else [])
    items = [i for i in qs if not levels or i.my_priority in levels or i.claude_priority in levels]
    model = pick_model(d.get('model'), settings.RESEARCH_COMPANY_MODEL)
    queued = sum(1 for i in items if queue_refresh(i, model, request.user))
    return Response({'queued': queued, 'skipped': len(items) - queued}, status=status.HTTP_202_ACCEPTED)


@api_view(['DELETE'])
@permission_classes([CanResearch])
def dismiss_news(request, news_id: int):
    NewsItem.objects.filter(id=news_id).update(hidden=True)  # kept so refreshes don't add it back
    return Response(status=status.HTTP_204_NO_CONTENT)
