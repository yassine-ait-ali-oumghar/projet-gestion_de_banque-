from django.urls import path
from cards import views

urlpatterns = [
    path('', views.cards_list, name='cards'),
    path('request/', views.request_card, name='request_card'),
    path('toggle/<int:card_id>/', views.toggle_card, name='toggle_card'),
    path('delete/<int:card_id>/', views.delete_card, name='delete_card'),
    path('payment/', views.card_payment, name='card_payment'),
]
