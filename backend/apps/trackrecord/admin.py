from django.contrib import admin

from .models import CashFlow, Investment, InvestmentComment, ManagerAssessment, ManagerComment, SheetSettings


class CashFlowInline(admin.TabularInline):
    model = CashFlow
    extra = 0


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'structure', 'invest_date', 'invested_usd_m', 'current_value_usd_m', 'status', 'include_in_sheet']
    list_filter = ['structure', 'status', 'include_in_sheet']
    search_fields = ['name', 'vehicle']
    inlines = [CashFlowInline]


admin.site.register([SheetSettings, InvestmentComment, ManagerAssessment, ManagerComment])
