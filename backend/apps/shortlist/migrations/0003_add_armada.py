"""Add Armada (modular / edge AI data centres) to the shortlist and refresh its tracker row (14-Nov-2026 ADCG-VG run).

Sachin's own priority is left unset for him to choose; Claude's view is L2.
Runs only where the tracker already holds Armada (the live book). Company data is merged additively: rounds and GP positions are only added when missing.
"""
from django.conf import settings
from django.db import migrations
from django.utils import timezone

SLUG = 'armada'
TODAY = '2026-11-14'

COMPANY = {
    'name': 'Armada',
    'website': 'https://www.armada.ai',
    'hq': 'San Francisco, CA, USA',
    'founded': 2022,
    'description': ('Factory-built modular / edge AI data centres (Galleon family: Beacon to 10 MW Orion, Leviathan) plus fleet '
                    'and GPU software (Commander/Atlas, Bridge, Armada Edge Platform) for defence, energy and sovereign AI; '
                    'manufactured with Johnson Controls in Dublin and Arizona.'),
    'sector': 'AI',
    'focus_tags': ['AI infra', 'Defense', 'Hardware / devices', 'Sovereign AI'],
    'status': 'Private',
    'latest_valuation_usd_bn': 2.21,
    'valuation_date': '2026-05',
    'valuation_label': 'REPORTED',
    'valuation_basis': 'Series B post-money ($2.0bn pre + $230m; $2.21bn per charter-derived Forge record)',
    'total_raised_usd_bn': 0.46,
    'growth': 'Bookings +540% FY25->FY26; Q1 FY27 bookings +2,000% YoY (company-stated, base undisclosed)',
    'profitability': 'Undisclosed',
    'ceo': 'Dan Wright',
    'notes': ('ADCG-VG 5.67 (Neutral) / Venture Risk 63 (14-Nov-26). Revenue, margin and backlog undisclosed. '
              'Forge One (AZ) production slipped from summer-26 to early-27; Forge Two (Dublin) producing since Nov-26. '
              'NVIDIA DSX POD partner (one of 17); Palantir certified modular DC partner; JCI target >=500 MW in 2027.'),
    'sources': [
        'https://www.prnewswire.com/news-releases/armada-announces-agreement-with-johnson-controls-for-galleon-forge-one-raises-230m-in-oversubscribed-series-b-with-a-pre-money-valuation-of-2b-to-accelerate-deployment-of-the-us-ai-stack-and-support-explosive-customer-demand--302775720.html',
        'https://www.datacenterdynamics.com/en/news/edge-data-center-firm-armada-raises-230m-in-latest-funding-round/',
        'https://www.forbes.com/sites/alexkonrad/2023/12/11/armada-edge-computing-ai-spacex-starlink/',
        'https://www.armada.ai/blog/131M-strategic-funding-leviathan',
        'https://www.johnsoncontrols.com/media-center/news/press-releases/2026/11/11/armada-and-johnson-controls-launch-galleon-forge-two-in-dublin',
    ],
    'last_verified': TODAY,
}
OTHER_INVESTORS = ['BlackRock', 'Overmatch Ventures', '8090 Industries', 'Shield Capital', 'Johnson Controls', 'Mitsui',
                   'Singtel Innov8', 'NightDragon', 'M12 (Microsoft)', 'Marlinspike', 'Silent Ventures', 'Veriten',
                   'Glade Brook', 'Pinegrove', 'Valor Equity Partners', 'Contrary', '137 Ventures']
ROUNDS = [
    ('2023-12', 'Series A (stealth exit, $55m+)', 0.245, 'Founders Fund, Lux Capital, Shield Capital, 8090 Industries'),
    ('2024-07', 'Strategic ($40m)', None, 'M12 (Microsoft)'),
    ('2025-07', 'Strategic ($131m)', None, None),
    ('2026-05', 'Series B', 2.21, 'Overmatch, BlackRock, 8090 Industries'),
]
POSITIONS = [  # firm slug, first year, entry round, lead
    ('founders-fund', 2023, 'Seed', True),
    ('lux', 2023, 'Seed', True),
    ('felicis', 2023, 'Series A', False),
    ('8vc', 2023, 'Series A', False),
]

RATIONALE = ('Best-evidenced name in the VG ledger so far (ADCG-VG 5.67 / risk 63): shipping product, named customers '
             '(US Navy, Aramco Digital, Fossefall, Aker BP), two JCI factories and a bookings ramp; VJR 1.41. Held at L2 '
             'because it is an integrator squeezed between NVIDIA and JCI, NVIDIA DSX POD standardises the container '
             '(17 partners), and revenue / margin are undisclosed. Would move to L1 on disclosed gross profit per MW '
             '>=25% GM and >=100 MW contracted 2027 deliveries; to L3 if Forge One slips past Q2-27 or a Series C '
             'prices >2.5x without revenue.')
THESIS = ('Factory-built sovereign / edge AI capacity sited at stranded power; GCC sovereign-AI angle (Aramco, Mekdam). '
          'Lux, Founders Fund and Felicis on the cap table.')
ROUNDS_PLAN = ('Do not chase a step-up now. Target the 2027 Series C (<=2x the B, gated on revenue/GM disclosure) or a '
               'secondary at <=$17.12/share; ask for pro-rata, info rights and GCC co-invest access.')
CATALYSTS = [
    {'text': 'Forge One (Arizona) continuous production — now guided early 2027', 'severity': 'high'},
    {'text': 'First NVIDIA DSX POD / Vera Rubin deliveries from early 2027', 'severity': 'high'},
    {'text': 'Fossefall 5 x Leviathan (>9 MW) delivered by Q1-27', 'severity': 'medium'},
    {'text': 'Series C or revenue disclosure', 'severity': 'medium'},
]
RISKS = [
    {'text': 'No revenue, gross margin or backlog ever disclosed', 'severity': 'high'},
    {'text': 'DSX POD commoditises the box: Dell, HPE, Schneider, Vertiv ship the same design', 'severity': 'high'},
    {'text': 'JCI is investor, sole manufacturer and a modular-DC competitor', 'severity': 'medium'},
    {'text': 'Mark struck at the 2026 AI-infra peak; public anchors de-rated Oct–Nov 26', 'severity': 'medium'},
]
NEWS = [
    ('2026-11-11', 'Armada and Johnson Controls start production at Galleon Forge Two in Dublin', 'product', 'high',
     'Johnson Controls', 'https://www.johnsoncontrols.com/media-center/news/press-releases/2026/11/11/armada-and-johnson-controls-launch-galleon-forge-two-in-dublin'),
    ('2026-10-21', 'Armada joins NVIDIA DSX POD; plans >=500 MW with Johnson Controls in 2027', 'product', 'high',
     'Data Centre Magazine', 'https://datacentremagazine.com/news/armada-johnson-controls-to-deploy-500mw-of-compute-in-2027'),
    ('2026-10-01', 'Palantir names Armada its inaugural certified modular data center partner', 'customers', 'medium',
     'HPCwire', 'https://www.hpcwire.com/bigdatawire/this-just-in/palantir-and-armada-partner-to-accelerate-sovereign-ai-infrastructure/'),
    ('2026-05-19', 'Armada raises $230m Series B at $2bn pre-money; JCI framework agreement', 'funding', 'high',
     'DCD', 'https://www.datacenterdynamics.com/en/news/edge-data-center-firm-armada-raises-230m-in-latest-funding-round/'),
]


def add(apps, schema_editor):
    Company = apps.get_model('companies', 'Company')
    Manager = apps.get_model('managers', 'Manager')
    Position = apps.get_model('companies', 'Position')
    Item = apps.get_model('shortlist', 'ShortlistItem')
    Change = apps.get_model('shortlist', 'PriorityChange')
    News = apps.get_model('shortlist', 'NewsItem')
    Job = apps.get_model('research', 'ResearchJob')
    now = timezone.now()

    co = Company.objects.filter(slug=SLUG).first() or Company.objects.filter(name__iexact='Armada').first()
    if co is None:  # fresh database: backend/data/tracker.json carries the same Armada data for the first import
        return
    for k, v in COMPANY.items():
        setattr(co, k, v)
    co.other_investors = sorted(set(co.other_investors or []) | set(OTHER_INVESTORS))
    co.first_mark_usd_bn, co.first_mark_date = 0.245, '2023-12'
    co.step_up_x = round(2.21 / 0.245, 1)
    co.save()

    have = {((r.date or '')[:7], (r.round or '').lower()) for r in co.rounds.all()}
    for date, rnd, post, lead in ROUNDS:
        same_month = [r for r in co.rounds.all() if (r.date or '')[:7] == date]
        if same_month:  # fill gaps on an existing row for that month instead of duplicating it
            r = same_month[0]
            if r.post_money_usd_bn is None and post is not None:
                r.post_money_usd_bn = post
            if not r.lead and lead:
                r.lead = lead
            r.save()
        elif (date, rnd.lower()) not in have:
            co.rounds.create(date=date, round=rnd, post_money_usd_bn=post, lead=lead or '')

    for fid, year, rnd, lead in POSITIONS:
        m = Manager.objects.filter(slug=fid).first()
        if not m:
            continue
        p = Position.objects.filter(company=co, manager=m).first()
        if p is None:
            Position.objects.create(company=co, manager=m, first_invest_year=year, entry_round=rnd, lead=lead,
                                    entry_post_usd_bn=0.245 if rnd == 'Series A' else None, via='ADCG-VG run 2026-11-14')
        else:
            p.first_invest_year = p.first_invest_year or year
            p.entry_round = p.entry_round or rnd
            p.lead = p.lead or lead
            p.save()

    if Item.objects.filter(company=co).exists():
        return
    item = Item.objects.create(kind='company', name=co.name, company=co,
                               my_priority='', claude_priority='L2', claude_priority_since=now, claude_rationale=RATIONALE,
                               thesis=THESIS, rounds_plan=ROUNDS_PLAN, momentum='up',
                               brief=('Series B $230m @ $2.0bn pre (May-26). Since then: Orion 10 MW, Fossefall order, Palantir '
                                      'partnership, NVIDIA DSX POD, Forge Two live. Forge One slipped to early 2027.'),
                               performance='Revenue / margins undisclosed; bookings +540% FY26, Q1 FY27 +2,000% YoY (MGMT).',
                               next_round='Likely 2027 Series C; no talks reported as of 14-Nov-26.',
                               catalysts=CATALYSTS, risks=RISKS, sources=COMPANY['sources'], last_refreshed_at=now)
    Change.objects.create(item=item, track='claude', old='', new='L2', changed_by='Claude (ADCG-VG run)',
                          note=f'Added 14-Nov-26 from the ADCG Venture Growth memo. {RATIONALE}')
    for date, head, cat, imp, src, url in NEWS:
        News.objects.create(item=item, date=date, headline=head, category=cat, importance=imp, source=src, url=url)
    if settings.ANTHROPIC_API_KEY:
        Job.objects.create(kind='shortlist', name=item.name, slug=str(item.id), model=settings.RESEARCH_COMPANY_MODEL)
        item.research_status = 'queued'
        item.save(update_fields=['research_status'])


def remove(apps, schema_editor):
    apps.get_model('shortlist', 'ShortlistItem').objects.filter(company__slug=SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('shortlist', '0002_seed_shortlist'),
        ('companies', '0004_company_investor_sources_and_more'),
        ('managers', '0003_manager_profile_manager_profile_status_and_more'),
        ('research', '0005_alter_researchjob_kind'),
    ]
    operations = [migrations.RunPython(add, remove)]
