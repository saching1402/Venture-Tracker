from django.contrib import admin

from .models import Company, Position, ValuationRound


class RoundInline(admin.TabularInline):
    model = ValuationRound
    extra = 0


class PositionInline(admin.TabularInline):
    model = Position
    extra = 0
    autocomplete_fields = ['manager']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'sector', 'status', 'latest_valuation_usd_bn', 'valuation_date', 'revenue_usd_bn', 'last_verified']
    list_filter = ['sector', 'legacy', 'valuation_stale']
    search_fields = ['name', 'slug', 'ceo']
    inlines = [RoundInline, PositionInline]
