from rest_framework import serializers

from .models import Company, Position, ValuationRound

LIST_FIELDS = [
    'id', 'name', 'description', 'sector', 'focus_tags', 'status', 'hq', 'ceo',
    'latest_valuation_usd_bn', 'valuation_date', 'valuation_label', 'valuation_stale', 'legacy',
    'first_mark_date', 'step_up_x', 'revenue_usd_bn', 'revenue_metric', 'revenue_date', 'ev_rev_x',
    'growth', 'profitability', 'total_raised_usd_bn', 'founded', 'tracked_gp_ids', 'other_investors',
]


class CompanyListSerializer(serializers.ModelSerializer):
    """Compact row; the frontend filters and sorts the full universe client-side."""
    id = serializers.CharField(source='slug')
    tracked_gp_ids = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = LIST_FIELDS

    def get_tracked_gp_ids(self, obj: Company) -> list[str]:
        return sorted(p.manager.slug for p in obj.positions.all())


class RoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValuationRound
        fields = ['date', 'round', 'post_money_usd_bn', 'lead']


class PositionSerializer(serializers.ModelSerializer):
    firm_id = serializers.CharField(source='manager.slug')
    firm_name = serializers.CharField(source='manager.name')

    class Meta:
        model = Position
        fields = ['firm_id', 'firm_name', 'first_invest_year', 'entry_round', 'fund', 'lead', 'via',
                  'entry_post_usd_bn', 'markup_x']


class CompanyDetailSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='slug')
    valuation_history = RoundSerializer(source='rounds', many=True, read_only=True)
    gp_positions = PositionSerializer(source='positions', many=True, read_only=True)

    class Meta:
        model = Company
        exclude = ['slug', 'managers']


class HoldingSerializer(serializers.ModelSerializer):
    """A manager's position joined with the company's headline figures."""
    company_id = serializers.CharField(source='company.slug')
    name = serializers.CharField(source='company.name')
    sector = serializers.CharField(source='company.sector')
    status = serializers.CharField(source='company.status')
    latest_valuation_usd_bn = serializers.FloatField(source='company.latest_valuation_usd_bn')
    revenue_usd_bn = serializers.FloatField(source='company.revenue_usd_bn')
    legacy = serializers.BooleanField(source='company.legacy')
    valuation_stale = serializers.BooleanField(source='company.valuation_stale')

    class Meta:
        model = Position
        fields = ['company_id', 'name', 'sector', 'status', 'latest_valuation_usd_bn', 'revenue_usd_bn', 'legacy',
                  'valuation_stale', 'first_invest_year', 'entry_round', 'lead', 'via', 'entry_post_usd_bn', 'markup_x']
