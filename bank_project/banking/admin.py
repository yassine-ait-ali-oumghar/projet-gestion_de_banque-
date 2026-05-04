from django.contrib import admin
from .models import Account, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'type', 'balance', 'date_creation')
    list_filter = ('type', 'date_creation')
    search_fields = ('account_number', 'user__username')
    readonly_fields = ('date_creation',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'amount', 'sender', 'receiver', 'status', 'date')
    list_filter = ('type', 'status', 'date')
    search_fields = ('sender__account_number', 'receiver__account_number')
    readonly_fields = ('date',)
