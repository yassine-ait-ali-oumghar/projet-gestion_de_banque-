from django.contrib import admin

from .models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('card_number', 'account', 'status', 'expiration_date', 'plafond')
    list_filter = ('status', 'expiration_date')
    search_fields = ('card_number', 'account__account_number')
