"""
URL configuration for bank_project project.
"""
from django.contrib import admin
from django.urls import path, include
from bank_project import views

admin.site.site_header = 'NovaBank'
admin.site.site_title = 'NovaBank Django'
admin.site.index_title = 'Accueil administratif'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('administration/', include('administration.urls')),
    path('', views.home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('banking/', include('banking.urls')),
    path('notifications/', include('notifications.urls')),
    path('cards/', include('cards.urls')),
]
