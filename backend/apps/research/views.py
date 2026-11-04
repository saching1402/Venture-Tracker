"""Add manager / Add company: create the entry immediately, research it in the background."""
from django.conf import settings
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.companies.models import Company
from apps.managers.models import Manager

from .engine import find_company, find_manager, unique_slug
from .models import ResearchJob


class CanResearch(BasePermission):
    message = 'Your account is view-only. Ask an admin to make you an analyst to add managers or companies.'

    def has_permission(self, request, view) -> bool:
        u = request.user
        return bool(u and u.is_authenticated and (u.is_staff or getattr(u, 'role', '') in ('admin', 'analyst')))


def can_research(user) -> bool:
    return CanResearch().has_permission(type('R', (), {'user': user})(), None)


def job_json(j: ResearchJob) -> dict:
    kids = getattr(j, 'n_children', 0)
    return {
        'id': str(j.id), 'kind': j.kind, 'name': j.name, 'slug': j.slug, 'status': j.status,
        'error': j.error, 'summary': j.summary, 'include_portfolio': j.include_portfolio,
        'children_total': kids, 'children_done': getattr(j, 'n_done', 0), 'children_failed': getattr(j, 'n_failed', 0),
        'searches': j.searches, 'cost_usd': j.cost_usd,
        'created_at': j.created_at.isoformat(), 'finished_at': j.finished_at.isoformat() if j.finished_at else None,
    }


def _jobs_qs():
    return (ResearchJob.objects.filter(parent__isnull=True)
            .annotate(n_children=Count('children'),
                      n_done=Count('children', filter=Q(children__status='done')),
                      n_failed=Count('children', filter=Q(children__status='failed'))))


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def research(request):
    if request.method == 'GET':
        jobs = list(_jobs_qs()[:30])
        active = ResearchJob.objects.filter(status__in=['queued', 'running']).count()
        return Response({'enabled': bool(settings.ANTHROPIC_API_KEY), 'can_research': can_research(request.user),
                         'active': active, 'jobs': [job_json(j) for j in jobs]})

    if not can_research(request.user):
        return Response({'detail': CanResearch.message}, status=status.HTTP_403_FORBIDDEN)
    if not settings.ANTHROPIC_API_KEY:
        return Response({'detail': 'Auto-research is off. Add ANTHROPIC_API_KEY to the Railway service variables, then try again.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    kind = request.data.get('kind')
    name = str(request.data.get('name') or '').strip()[:255]
    website = str(request.data.get('website') or '').strip()[:500]
    existing_slug = str(request.data.get('id') or '').strip()
    if kind not in ('manager', 'company') or (not name and not existing_slug):
        return Response({'detail': 'Send kind ("manager" or "company") and a name.'}, status=status.HTTP_400_BAD_REQUEST)
    model = Manager if kind == 'manager' else Company

    if existing_slug:  # re-research an existing row
        obj = model.objects.filter(slug=existing_slug).first()
        if not obj:
            return Response({'detail': f'Unknown {kind}: {existing_slug}'}, status=status.HTTP_404_NOT_FOUND)
    else:
        obj = find_manager(name) if kind == 'manager' else find_company(name, website)
        if obj and not request.data.get('refresh'):
            return Response({'detail': f'{obj.name} is already tracked.', 'id': obj.slug, 'exists': True},
                            status=status.HTTP_409_CONFLICT)
        if not obj:
            obj = model.objects.create(slug=unique_slug(model, name, 64 if kind == 'manager' else 96), name=name,
                                       website=website, added_via='user',
                                       **({'is_stub': True} if kind == 'manager' else {}))
    if ResearchJob.objects.filter(kind=kind, slug=obj.slug, status__in=['queued', 'running']).exists():
        return Response({'detail': f'{obj.name} is already being researched.', 'id': obj.slug},
                        status=status.HTTP_409_CONFLICT)
    obj.research_status = 'queued'
    obj.save(update_fields=['research_status'])
    job = ResearchJob.objects.create(kind=kind, name=obj.name, website=website or obj.website, slug=obj.slug,
                                     include_portfolio=kind == 'manager' and bool(request.data.get('include_portfolio', True)),
                                     created_by=request.user)
    return Response({'id': obj.slug, 'job': job_json(job)}, status=status.HTTP_202_ACCEPTED)


@api_view(['POST'])
@permission_classes([CanResearch])
def retry(request, job_id):
    job = ResearchJob.objects.filter(id=job_id).first()
    if not job:
        return Response({'detail': 'Unknown research job.'}, status=status.HTTP_404_NOT_FOUND)
    retried = 0
    for j in [job, *job.children.filter(status='failed')]:
        if j.status == 'failed':
            j.status, j.error, j.finished_at = 'queued', '', None
            j.save(update_fields=['status', 'error', 'finished_at'])
            (Manager if j.kind == 'manager' else Company).objects.filter(slug=j.slug).update(research_status='queued')
            retried += 1
    return Response({'retried': retried})
