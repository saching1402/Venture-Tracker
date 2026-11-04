from rest_framework import serializers

from apps.companies.models import Company
from apps.managers.models import Manager

from .metrics import compute
from .models import CashFlow, Investment, InvestmentComment, SheetSettings

SEVERITIES = {'high', 'medium', 'low'}


def clean_points(value) -> list[dict]:
    """Accept ["text", …] or [{"text", "severity"}, …]; return the normalised list."""
    if value in (None, ''):
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError('Must be a list.')
    out = []
    for item in value[:30]:
        if isinstance(item, str):
            item = {'text': item}
        if not isinstance(item, dict):
            raise serializers.ValidationError('Each point must be text or {"text", "severity"}.')
        text = str(item.get('text') or '').strip()[:600]
        if not text:
            continue
        sev = str(item.get('severity') or 'medium').lower()
        out.append({'text': text, 'severity': sev if sev in SEVERITIES else 'medium'})
    return out


def clean_names(value) -> list[str]:
    if value in (None, ''):
        return []
    if isinstance(value, str):
        value = value.split(',')
    if not isinstance(value, list):
        raise serializers.ValidationError('Must be a list of names.')
    return [str(v).strip()[:200] for v in value if str(v).strip()][:40]


class CashFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlow
        fields = ['date', 'amount_usd_m', 'note']


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentComment
        fields = ['id', 'author_name', 'text', 'created_at']


class InvestmentSerializer(serializers.ModelSerializer):
    company_id = serializers.SlugRelatedField(source='company', slug_field='slug', queryset=Company.objects.all(),
                                              required=False, allow_null=True)
    manager_id = serializers.SlugRelatedField(source='manager', slug_field='slug', queryset=Manager.objects.all(),
                                              required=False, allow_null=True)
    manager_name = serializers.CharField(source='manager.name', read_only=True, default='')
    is_fund = serializers.BooleanField(read_only=True)
    cashflows = CashFlowSerializer(many=True, required=False)
    comments = CommentSerializer(many=True, read_only=True)
    structure_label = serializers.CharField(source='get_structure_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = Investment
        exclude = ['company', 'manager']
        read_only_fields = ['created_at', 'updated_at']

    def get_metrics(self, obj: Investment) -> dict:
        latest = obj.company.latest_valuation_usd_bn if obj.company_id else None
        m = compute(obj, latest_company_valuation=latest)
        return {k: v for k, v in m.items() if not k.startswith('_')}

    def validate_pros(self, v):
        return clean_points(v)

    def validate_cons(self, v):
        return clean_points(v)

    def validate_risks(self, v):
        return clean_points(v)

    def validate_lead_investors(self, v):
        return clean_names(v)

    def validate_co_investors(self, v):
        return clean_names(v)

    def validate(self, data):
        for f in ('invested_usd_m', 'commitment_usd_m', 'current_value_usd_m', 'realised_usd_m', 'capacity_usd_m'):
            if data.get(f) is not None and data[f] < 0:
                raise serializers.ValidationError({f: 'Must be zero or more.'})
        for f in ('mgmt_fee_pct', 'carry_pct'):
            if data.get(f) is not None and not 0 <= data[f] <= 100:
                raise serializers.ValidationError({f: 'Enter a percentage between 0 and 100.'})
        return data

    def _save_flows(self, inv: Investment, flows):
        if flows is None:
            return
        inv.cashflows.all().delete()
        CashFlow.objects.bulk_create([CashFlow(investment=inv, **f) for f in flows if f.get('amount_usd_m')])

    def create(self, validated):
        flows = validated.pop('cashflows', None)
        inv = super().create(validated)
        self._save_flows(inv, flows)
        return inv

    def update(self, inv, validated):
        flows = validated.pop('cashflows', None)
        inv = super().update(inv, validated)
        self._save_flows(inv, flows)
        return inv


class SheetSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SheetSettings
        exclude = ['id']


class AssessmentSerializer(serializers.Serializer):
    view = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    pros = serializers.JSONField(required=False)
    cons = serializers.JSONField(required=False)
    risks = serializers.JSONField(required=False)

    def validate_pros(self, v):
        return clean_points(v)

    def validate_cons(self, v):
        return clean_points(v)

    def validate_risks(self, v):
        return clean_points(v)
