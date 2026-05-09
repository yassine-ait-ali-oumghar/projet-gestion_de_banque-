from django.urls import path
from . import views

urlpatterns = [
    path('accounts/', views.accounts_list, name='accounts_list'),
    path('accounts/create/', views.create_account, name='create_account'),
    path('deposit/', views.deposit, name='deposit'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('transfer/', views.transfer, name='transfer'),
    path('transactions/', views.transactions_list, name='transactions'),
    path('export-pdf/', views.export_transactions_pdf, name='export_pdf'),
]
