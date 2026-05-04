from django.urls import path
from . import views

urlpatterns = [
    path('', views.cards_list, name='cards'),
    path('request/', views.request_card, name='request_card'),
    path('toggle/<int:card_id>/', views.toggle_card, name='toggle_card'),
]
