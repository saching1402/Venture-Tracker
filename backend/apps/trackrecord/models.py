"""
The LP's own investments ("Track Record" tab and marketing sheet).

Amounts are USD millions; valuations are USD billions (same as the rest of the tracker).
Cash-flow sign convention: negative = money invested, positive = money returned.
"""
from django.db import models

from apps.companies.models import Company
from apps.managers.models import Manager


class SheetSettings(models.Model):
    """Singleton (pk=1): text printed on the marketing sheet."""
    title = models.CharField(max_length=200, default='Investment Track Record')
    subtitle = models.CharField(max_length=300, blank=True, default='Venture and growth direct investments, co-investments and fund positions')
    prepared_by = models.CharField(max_length=200, blank=True)
    contact = models.CharField(max_length=300, blank=True)
    disclaimer = models.TextField(blank=True, default=(
        'For discussion purposes only. Not an offer to sell or a solicitation of an offer to buy any security. '
        'Values for unrealised positions are estimates based on the latest available marks and may not be realised. '
        'Net figures are estimated after the stated fees and carry unless marked as reported. Past performance is not '
        'indicative of future results.'))
    show_capacity = models.BooleanField(default=True)
    fund_title = models.CharField(max_length=200, default='Fund Programme Track Record')
    fund_subtitle = models.CharField(max_length=300, blank=True, default='Primary and secondary fund commitments by vintage and strategy')

    class Meta:
        db_table = 'trackrecord_settings'

    @classmethod
    def get(cls) -> 'SheetSettings':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Investment(models.Model):
    STRUCTURES = [
        ('direct', 'Direct (cap table)'),
        ('spv', 'SPV'),
        ('coinvest', 'Co-investment'),
        ('l1', 'L1 fund'),
        ('l2', 'L2 fund-of-funds'),
        ('secondary', 'Secondary'),
    ]
    STATUSES = [('active', 'Active'), ('partial', 'Partially realised'), ('realised', 'Realised'), ('written_off', 'Written off')]

    name = models.CharField(max_length=255)
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name='lp_investments',
                                help_text='Optional link to a tracked company (fills description, sector, investors)')
    manager = models.ForeignKey(Manager, null=True, blank=True, on_delete=models.SET_NULL, related_name='lp_investments',
                                help_text='For fund commitments (L1 / L2): the GP')
    vintage = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Fund vintage year')
    description = models.TextField(blank=True)
    sector = models.CharField(max_length=64, blank=True)
    hq = models.CharField(max_length=255, blank=True)

    structure = models.CharField(max_length=12, choices=STRUCTURES, default='direct')
    vehicle = models.CharField(max_length=255, blank=True, help_text='SPV / fund name, e.g. "Tech Co-Invest SPV I"')
    round = models.CharField(max_length=120, blank=True)
    lead_investors = models.JSONField(default=list, blank=True)
    co_investors = models.JSONField(default=list, blank=True, help_text='Invested alongside')

    invest_date = models.DateField()
    commitment_usd_m = models.FloatField(null=True, blank=True, help_text='Fund / SPV commitment; blank for a direct cheque')
    invested_usd_m = models.FloatField(help_text='Initial cheque (or capital called to date for a fund)')
    entry_valuation_usd_bn = models.FloatField(null=True, blank=True, help_text='Post-money of the round invested in')
    ownership_pct = models.FloatField(null=True, blank=True, help_text='Fully diluted %, if known')

    current_value_usd_m = models.FloatField(null=True, blank=True, help_text='Unrealised value (gross)')
    value_date = models.DateField(null=True, blank=True)
    value_basis = models.CharField(max_length=120, blank=True, help_text='e.g. Last round, GP NAV, public price')
    realised_usd_m = models.FloatField(default=0, help_text='Proceeds received to date (if not entered as cash flows)')

    mgmt_fee_pct = models.FloatField(default=0, help_text='Annual fee on invested capital, % (SPV / fund)')
    carry_pct = models.FloatField(default=0, help_text='Carried interest on gains, %')
    net_moic_reported = models.FloatField(null=True, blank=True, help_text='GP-reported net MOIC, overrides the estimate')
    net_irr_reported = models.FloatField(null=True, blank=True, help_text='GP-reported net IRR in %, overrides the estimate')
    dpi_reported = models.FloatField(null=True, blank=True, help_text='GP-reported net DPI, overrides the estimate')

    capacity_usd_m = models.FloatField(null=True, blank=True, help_text='Allocation still available to co-investors')
    status = models.CharField(max_length=12, choices=STATUSES, default='active')
    highlight = models.TextField(blank=True, help_text='One or two lines for the marketing sheet')
    thesis = models.TextField(blank=True, help_text='Investment thesis / your view')
    # [{"text": "...", "severity": "high" | "medium" | "low"}]
    pros = models.JSONField(default=list, blank=True)
    cons = models.JSONField(default=list, blank=True)
    risks = models.JSONField(default=list, blank=True)
    include_in_sheet = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trackrecord_investments'
        ordering = ['order', '-invest_date', 'name']

    def __str__(self) -> str:
        return self.name

    @property
    def is_fund(self) -> bool:
        return self.structure in ('l1', 'l2')


class CashFlow(models.Model):
    """Follow-ons (negative) and distributions (positive) after the initial cheque."""
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='cashflows')
    date = models.DateField()
    amount_usd_m = models.FloatField()
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'trackrecord_cashflows'
        ordering = ['date', 'id']


class InvestmentComment(models.Model):
    """Dated comment log on an investment (internal; optional on the PDF)."""
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL)
    author_name = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trackrecord_comments'
        ordering = ['-created_at']


class ManagerAssessment(models.Model):
    """Your view on a GP / fund: pros, cons, risks (shown on the manager profile)."""
    manager = models.OneToOneField(Manager, on_delete=models.CASCADE, related_name='assessment')
    view = models.TextField(blank=True, help_text='Overall view / thesis on the manager')
    pros = models.JSONField(default=list, blank=True)
    cons = models.JSONField(default=list, blank=True)
    risks = models.JSONField(default=list, blank=True)
    updated_by = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'manager_assessments'


class ManagerComment(models.Model):
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE, related_name='lp_comments')
    author = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL)
    author_name = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'manager_comments'
        ordering = ['-created_at']
