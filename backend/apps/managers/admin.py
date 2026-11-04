from django.contrib import admin

from .models import Fund, KeyPerson, Manager


class FundInline(admin.TabularInline):
    model = Fund
    extra = 0


class PersonInline(admin.TabularInline):
    model = KeyPerson
    extra = 0


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'hq', 'aum_usd_bn', 'last_verified']
    list_filter = ['type']
    search_fields = ['name', 'slug', 'hq']
    inlines = [FundInline, PersonInline]
