"""Track Record API: investments CRUD with computed metrics, comments, sheet settings, PDF."""
import datetime as dt

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.companies.models import Company
from apps.research.views import can_research as can_edit

from .metrics import compute, fund_programme, summarise
from apps.managers.models import Manager

from .models import Investment, InvestmentComment, ManagerAssessment, ManagerComment, SheetSettings
from .pdf import render_pdf
from .serializers import AssessmentSerializer, CommentSerializer, InvestmentSerializer, SheetSettingsSerializer


class ReadOrEdit(BasePermission):
    """Everyone signed in can read; admins and analysts can change."""
    message = 'Your account is view-only. Ask an admin to make you an analyst to edit the track record.'

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or can_edit(request.user)


def _queryset():
    return Investment.objects.select_related('company').prefetch_related('cashflows', 'comments')


def _rows(qs):
    return [(i, compute(i, latest_company_valuation=i.company.latest_valuation_usd_bn if i.company_id else None)) for i in qs]


def _summary_json(rows) -> dict:
    return summarise(rows)


VIEWS = ('all', 'direct', 'funds')


def apply_filters(invs: list[Investment], params) -> list[Investment]:
    """Filters shared by the tab and the PDF: view (all / direct / funds), structure, status, sector, search."""
    view = params.get('view') or params.get('kind') or 'all'
    if view == 'direct':
        invs = [i for i in invs if not i.is_fund]
    elif view == 'funds':
        invs = [i for i in invs if i.is_fund]
    for field in ('structure', 'status', 'sector'):
        wanted = {v for v in str(params.get(field) or '').split(',') if v}
        if wanted:
            invs = [i for i in invs if getattr(i, field) in wanted]
    q = str(params.get('q') or '').strip().lower()
    if q:
        def hay(i: Investment) -> str:
            return ' '.join([i.name, i.vehicle, i.round, i.sector, i.description, i.manager.name if i.manager_id else '',
                             ' '.join(i.lead_investors or []), ' '.join(i.co_investors or [])]).lower()
        invs = [i for i in invs if q in hay(i)]
    return invs


def facets(invs: list[Investment]) -> dict:
    """Options for the filter bar, from the unfiltered book."""
    return {
        'structures': [{'id': k, 'label': v, 'count': sum(1 for i in invs if i.structure == k)}
                       for k, v in Investment.STRUCTURES if any(i.structure == k for i in invs)],
        'statuses': [{'id': k, 'label': v, 'count': sum(1 for i in invs if i.status == k)}
                     for k, v in Investment.STATUSES if any(i.status == k for i in invs)],
        'sectors': sorted({i.sector for i in invs if i.sector}),
        'total': len(invs),
        'direct': sum(1 for i in invs if not i.is_fund),
        'funds': sum(1 for i in invs if i.is_fund),
    }


class InvestmentViewSet(viewsets.ModelViewSet):
    serializer_class = InvestmentSerializer
    permission_classes = [ReadOrEdit]
    pagination_class = None

    def get_queryset(self):
        return _queryset()

    def list(self, request, *args, **kwargs):
        everything = list(self.get_queryset().select_related('manager'))
        qs = apply_filters(everything, request.query_params)
        sheet = [i for i in qs if i.include_in_sheet]
        rows = _rows(qs)
        return Response({
            'investments': InvestmentSerializer(qs, many=True).data,
            'summary': _summary_json(rows),
            'summary_direct': _summary_json([r for r in rows if not r[0].is_fund]),
            'summary_funds': _summary_json([r for r in rows if r[0].is_fund]),
            'fund_programme': {k: v for k, v in fund_programme(rows).items()},
            'sheet_summary': _summary_json(_rows(sheet)),
            'settings': SheetSettingsSerializer(SheetSettings.get()).data,
            'can_edit': can_edit(request.user),
            'facets': facets(everything),
        })

    @action(detail=True, methods=['post'])
    def comments(self, request, pk=None):
        inv = self.get_object()
        text = str(request.data.get('text') or '').strip()
        if not text:
            return Response({'detail': 'Write a comment first.'}, status=status.HTTP_400_BAD_REQUEST)
        u = request.user
        c = InvestmentComment.objects.create(investment=inv, author=u, text=text[:5000],
                                             author_name=getattr(u, 'full_name', '') or u.email)
        return Response(CommentSerializer(c).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([ReadOrEdit])
def delete_comment(request, comment_id):
    c = get_object_or_404(InvestmentComment, id=comment_id)
    if c.author_id != request.user.id and not (request.user.is_staff or getattr(request.user, 'role', '') == 'admin'):
        return Response({'detail': 'Only the author or an admin can delete this comment.'}, status=status.HTTP_403_FORBIDDEN)
    c.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'PUT'])
@permission_classes([ReadOrEdit])
def sheet_settings(request):
    obj = SheetSettings.get()
    if request.method == 'PUT':
        ser = SheetSettingsSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
    return Response(SheetSettingsSerializer(obj).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def prefill(request):
    """Suggested fields when an investment is linked to a tracked company."""
    co = get_object_or_404(Company.objects.prefetch_related('rounds'), slug=request.query_params.get('company', ''))
    rounds = [r for r in co.rounds.all() if r.post_money_usd_bn]
    last = rounds[-1] if rounds else None
    leads = []
    for r in reversed(list(co.rounds.all())):
        for name in (r.lead or '').replace(' / ', ',').split(','):
            if name.strip() and name.strip() not in leads:
                leads.append(name.strip())
    return Response({
        'name': co.name, 'description': co.description, 'sector': co.sector, 'hq': co.hq,
        'lead_investors': leads[:5], 'co_investors': co.other_investors[:25],
        'latest_valuation_usd_bn': co.latest_valuation_usd_bn, 'valuation_date': co.valuation_date,
        'last_round': {'date': last.date, 'round': last.round, 'post_money_usd_bn': last.post_money_usd_bn} if last else None,
        'rounds': [{'date': r.date, 'round': r.round, 'post_money_usd_bn': r.post_money_usd_bn} for r in rounds],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pdf(request):
    """Marketing sheet PDF for what the tab shows: same filters as the list (view / kind, structure, status,
    sector, q). ?commentary=1 adds pros/cons/risks/comments; ?ids=1,2 limits rows."""
    kind = request.query_params.get('view') or request.query_params.get('kind') or 'all'
    kind = kind if kind in VIEWS else 'all'
    qs = _queryset().select_related('manager__assessment').filter(include_in_sheet=True)
    ids = [int(x) for x in request.query_params.get('ids', '').split(',') if x.strip().isdigit()]
    if ids:
        qs = _queryset().select_related('manager__assessment').filter(id__in=ids)
    rows = _rows(apply_filters(list(qs), request.query_params))
    body = render_pdf(rows, summarise(rows), SheetSettings.get(),
                      commentary=request.query_params.get('commentary') == '1', kind=kind)
    name = {'all': 'track-record', 'direct': 'direct-investments', 'funds': 'fund-programme'}[kind]
    resp = HttpResponse(body, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{name}-{dt.date.today().isoformat()}.pdf"'
    return resp


def _assessment_json(mgr: Manager) -> dict:
    a = ManagerAssessment.objects.filter(manager=mgr).first()
    invs = list(_queryset().filter(manager=mgr))
    return {
        'view': a.view if a else '', 'pros': a.pros if a else [], 'cons': a.cons if a else [],
        'risks': a.risks if a else [], 'updated_by': a.updated_by if a else '',
        'updated_at': a.updated_at.isoformat() if a else None,
        'comments': [{'id': c.id, 'author_name': c.author_name, 'text': c.text, 'created_at': c.created_at.isoformat()}
                     for c in mgr.lp_comments.all()[:100]],
        'commitments': InvestmentSerializer(invs, many=True).data,
    }


@api_view(['GET', 'PUT'])
@permission_classes([ReadOrEdit])
def manager_assessment(request, slug):
    """Your view on a GP: pros / cons / risks, comment log, and your commitments to its funds."""
    mgr = get_object_or_404(Manager, slug=slug)
    if request.method == 'PUT':
        ser = AssessmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        a, _ = ManagerAssessment.objects.get_or_create(manager=mgr)
        for k, v in ser.validated_data.items():
            setattr(a, k, v)
        a.updated_by = getattr(request.user, 'full_name', '') or request.user.email
        a.save()
    return Response(_assessment_json(mgr))


@api_view(['POST'])
@permission_classes([ReadOrEdit])
def manager_comment(request, slug):
    mgr = get_object_or_404(Manager, slug=slug)
    text = str(request.data.get('text') or '').strip()
    if not text:
        return Response({'detail': 'Write a comment first.'}, status=status.HTTP_400_BAD_REQUEST)
    u = request.user
    ManagerComment.objects.create(manager=mgr, author=u, text=text[:5000], author_name=getattr(u, 'full_name', '') or u.email)
    return Response(_assessment_json(mgr), status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([ReadOrEdit])
def delete_manager_comment(request, comment_id):
    c = get_object_or_404(ManagerComment, id=comment_id)
    if c.author_id != request.user.id and not (request.user.is_staff or getattr(request.user, 'role', '') == 'admin'):
        return Response({'detail': 'Only the author or an admin can delete this comment.'}, status=status.HTTP_403_FORBIDDEN)
    c.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
