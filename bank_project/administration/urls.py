from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='adm_dashboard'),
    path('utilisateurs/', views.users_list, name='adm_users'),
    path('comptes/', views.accounts_panel, name='adm_accounts'),
    path('transactions/', views.transactions_panel, name='adm_transactions'),
    path('utilisateurs/<int:pk>/toggle-actif/', views.toggle_user_active, name='adm_toggle_user'),
    path('comptes/<int:pk>/toggle-actif/', views.toggle_account_active, name='adm_toggle_account'),
]
