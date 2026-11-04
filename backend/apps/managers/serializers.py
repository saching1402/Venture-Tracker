from rest_framework import serializers

from .models import Fund, KeyPerson, Manager


class FundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fund
        fields = ['name', 'size_usd_bn', 'vintage', 'label']


class KeyPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyPerson
        fields = ['name', 'title', 'focus']


class ManagerListSerializer(serializers.ModelSerializer):
    """Compact row for the Managers table (whole universe loads in one request)."""
    id = serializers.CharField(source='slug')
    latest_fund = serializers.SerializerMethodField()
    n_companies = serializers.IntegerField(read_only=True)

    class Meta:
        model = Manager
        fields = ['id', 'name', 'type', 'hq', 'founded', 'aum_usd_bn', 'aum_label', 'stages', 'focus_areas',
                  'key_people_names', 'latest_fund', 'n_companies', 'is_stub', 'recent_activity']

    key_people_names = serializers.SerializerMethodField()

    def get_latest_fund(self, obj: Manager):
        funds = list(obj.funds.all())
        if not funds:
            return None
        f = max(funds, key=lambda x: x.vintage or 0)
        return {'name': f.name, 'size_usd_bn': f.size_usd_bn, 'vintage': f.vintage}

    def get_key_people_names(self, obj: Manager) -> list[str]:
        return [p.name for p in obj.people.all()]


class ManagerDetailSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='slug')
    recent_funds = FundSerializer(source='funds', many=True, read_only=True)
    key_people = KeyPersonSerializer(source='people', many=True, read_only=True)

    class Meta:
        model = Manager
        exclude = ['slug']
