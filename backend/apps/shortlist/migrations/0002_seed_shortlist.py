"""Seed the initial shortlist (Nov 2026) and queue a first web refresh for each when auto-research is on."""
from django.conf import settings
from django.db import migrations
from django.utils import timezone

INITIAL = 'Initial view at shortlist creation (from tracker data); the first web refresh re-assesses it.'

SEED = [
    # slug in the tracker, name, Claude's initial level, rationale
    ('anthropic', 'Anthropic', 'L1',
     'Frontier-model leader with the fastest enterprise / API revenue ramp in the category and frequent primary and '
     'tender windows, so there are repeated chances to add exposure. Main risks: entry price, compute capex and '
     'funding needs, and competition from OpenAI and Google. Would drop to L2 if growth slows or rounds price ahead of revenue.'),
    ('openai', 'OpenAI', 'L2',
     'Category scale leader, but LP access is mostly via SPV / secondary layers with fee stacking, the recapitalised '
     'structure and very large compute commitments add complexity, and the valuation already prices in leadership. '
     'Would move to L1 on a clean primary or tender allocation at a reasonable revenue multiple.'),
    ('andurilindustries', 'Anduril Industries', 'L1',
     'Defence-tech platform with a record of consistent up-rounds, growing programme-of-record wins and an IPO pathway; '
     'it also fits the defence-sector allocation. Risks: dependence on US budgets and contract timing, and manufacturing '
     'scale-up (Arsenal). Would move to L2 if contract momentum stalls or the round prices at a large premium to listed defence primes.'),
    ('physicalintelligence', 'Physical Intelligence', 'L2',
     'Leading robot foundation-model team with strong backers and high option value, but pre-revenue, priced richly '
     'for its stage, and the path to commercial deployment is unproven. Track monthly. Would move to L1 on credible '
     'commercial pilots or a round where co-invest access is available.'),
    ('baseten', 'Baseten', 'L2',
     'Fast-growing inference platform riding demand for model serving, with repeat up-rounds. But the category is crowded '
     '(Fireworks, Together, hyperscalers, neo-clouds) and gross margins depend on GPU pricing. Would move to L1 if it '
     'shows durable margin and enterprise retention ahead of peers.'),
    ('fireworks', 'Fireworks AI', 'L3',
     'Credible inference player with strong growth, but it overlaps Baseten in a commoditising layer; holding both adds '
     'concentration to the same risk. Watch for differentiation (custom silicon partnerships, enterprise wins) before prioritising.'),
]


def seed(apps, schema_editor):
    Item = apps.get_model('shortlist', 'ShortlistItem')
    Change = apps.get_model('shortlist', 'PriorityChange')
    Company = apps.get_model('companies', 'Company')
    Job = apps.get_model('research', 'ResearchJob')
    if Item.objects.exists():
        return
    now = timezone.now()
    for slug, name, claude, why in SEED:
        co = Company.objects.filter(slug=slug).first() or Company.objects.filter(name__iexact=name).first()
        item = Item.objects.create(kind='company', name=co.name if co else name, company=co,
                                   my_priority='L1', my_priority_since=now,
                                   claude_priority=claude, claude_priority_since=now, claude_rationale=why,
                                   thesis='Shortlisted to track closely and back across multiple rounds.')
        Change.objects.create(item=item, track='mine', old='', new='L1', changed_by='Sachin (initial shortlist)',
                              note='Flagged L1 when the shortlist was created.')
        Change.objects.create(item=item, track='claude', old='', new=claude, changed_by='Claude (initial view)',
                              note=f'{INITIAL} {why}')
        if settings.ANTHROPIC_API_KEY and co:
            Job.objects.create(kind='shortlist', name=item.name, slug=str(item.id),
                               model=settings.RESEARCH_COMPANY_MODEL)
            item.research_status = 'queued'
            item.save(update_fields=['research_status'])


def unseed(apps, schema_editor):
    apps.get_model('shortlist', 'ShortlistItem').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('shortlist', '0001_initial'),
        ('research', '0003_alter_researchjob_kind_alter_researchjob_slug'),
        ('companies', '0002_company_added_via_company_research_status'),
    ]
    operations = [migrations.RunPython(seed, unseed)]
