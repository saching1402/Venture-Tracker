"""Refresh one theme with Claude + web search (ResearchJob kind 'theme', slug = theme slug)."""
from __future__ import annotations

import datetime as dt
import json

from django.conf import settings

from apps.research.engine import ask_claude, parse_json
from apps.research.prompts import RULES

from .models import EARLY_MAX_USD_BN, Theme
from .services import apply_theme, export_trends

PROMPT = """Refresh the investable theme "{name}" for an institutional LP (Abu Dhabi allocator investing in US / Europe
venture and growth via funds, directs and co-investments). The LP's goal: deploy into the themes that will produce
the biggest outcomes, separately for EARLY (post-money below ${early}bn) and GROWTH (private, ${early}bn and above).

Current record (may be stale; keep what is still right, fix what is wrong):
{current}

Using web search, find what is material since {since}: funding totals for this theme (Crunchbase, PitchBook, CB Insights,
Dealroom, sector trackers such as Seraphim for space or the Fusion Industry Association), the largest rounds and
valuations, IPOs / M&A, new entrants, GP interviews and partner views (podcasts, YouTube, blogs), expert and operator
commentary, and policy or technology milestones. Prefer primary sources and best-in-class reports.

Return ONE JSON object in the same shape as the current record (keys: id, name, summary, why_now, deploy_view,
signal [accelerating|hot|steady|emerging|cooling], heat [0-100: capital momentum, round velocity, exits, narrative],
conviction [high|medium|low], horizon [now|1-3y|3-7y|7y+], deploy_early and deploy_growth [overweight|selective|watch|avoid],
funding [{{period, stage, capital_usd_bn, deals, note, source, url, label, metric: venture (VC raised) | market (spend / market size / capex)}}], valuation_notes, risks and catalysts
[{{text, severity}}], kpis [strings], segments [{{name, description, companies: [{{name, id (tracker id if given), domain,
stage [early|growth|public|acquired], hq, description, valuation_usd_bn, valuation_date YYYY-MM, valuation_label,
last_round, investors}}]}}], news [{{date YYYY-MM-DD, headline, url, source, summary}}] (new items only, up to 10),
resources [{{title, url, source, kind [report|article|news|interview|podcast|video|newsletter|data], date, summary}}]
(new, high-quality reading only, up to 10), sources [urls]).
Keep every existing company unless it has shut down; add important new ones. Use null for anything you cannot verify."""


def run_theme(job) -> str:
    theme = Theme.objects.get(slug=job.slug)
    cur = next(t for t in export_trends()['themes'] if t['id'] == theme.slug)
    cur.pop('resources', None)
    since = (theme.last_refreshed_at.date() - dt.timedelta(days=3)).isoformat() if theme.last_refreshed_at else '2026-01-01'
    text, usage = ask_claude(RULES.format(today=dt.date.today().isoformat()),
                             PROMPT.format(name=theme.name, early=EARLY_MAX_USD_BN, since=since,
                                           current=json.dumps(cur, separators=(',', ':'))[:60000]),
                             max_searches=10, max_tokens=16000, model=job.model)
    job.searches += usage['searches']
    job.input_tokens += usage['input_tokens']
    job.output_tokens += usage['output_tokens']
    job.cost += usage.get('cost', 0.0)
    job.save(update_fields=['searches', 'input_tokens', 'output_tokens', 'cost'])
    data = parse_json(text)
    data['id'] = theme.slug
    old_heat = theme.heat
    theme, added = apply_theme(data, via='refresh')
    moved = f', heat {old_heat} → {theme.heat}' if old_heat != theme.heat else ''
    return f'{theme.name}: refreshed; {added} new reading-list links{moved}.'


def queue_theme(theme: Theme, model: str = '', user=None):
    from apps.research.models import ResearchJob
    if ResearchJob.objects.filter(kind='theme', slug=theme.slug, status__in=['queued', 'running']).exists():
        return None
    model = model if model in settings.RESEARCH_MODELS else settings.RESEARCH_COMPANY_MODEL
    job = ResearchJob.objects.create(kind='theme', name=theme.name, slug=theme.slug, model=model, created_by=user)
    theme.research_status = 'queued'
    theme.save(update_fields=['research_status'])
    return job
