from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Card
from banking.models import Account
from notifications.models import Notification
import random
from datetime import date
from dateutil.relativedelta import relativedelta


@login_required
def cards_list(request):
    """Liste des cartes bancaires de l'utilisateur."""
    user_accounts = Account.objects.filter(user=request.user)
    cards = Card.objects.filter(account__in=user_accounts).select_related('account')
    return render(request, 'cards/cards.html', {
        'cards': cards,
        'accounts': user_accounts,
    })


@login_required
def request_card(request):
    """Demander une nouvelle carte bancaire."""
    if request.method == 'POST':
        account_id = request.POST.get('account')
        account = get_object_or_404(Account, id=account_id, user=request.user)
        card_number = ''.join([str(random.randint(0, 9)) for _ in range(16)])
        expiry = date.today() + relativedelta(years=3)
        card = Card.objects.create(
            account=account,
            card_number=card_number,
            expiration_date=expiry,
            status='active',
            plafond=10000.00,
        )
        Notification.objects.create(
            user=request.user,
            message=f'Nouvelle carte créée pour le compte {account.account_number}.',
            type='confirm_transaction',
        )
        messages.success(request, 'Carte bancaire créée avec succès.')
        return redirect('cards')
    accounts = Account.objects.filter(user=request.user)
    return render(request, 'cards/request_card.html', {'accounts': accounts})


@login_required
def toggle_card(request, card_id):
    """Activer/Désactiver une carte bancaire."""
    user_accounts = Account.objects.filter(user=request.user)
    card = get_object_or_404(Card, id=card_id, account__in=user_accounts)
    if card.status == 'active':
        card.status = 'inactive'
        msg = 'Carte désactivée.'
    else:
        card.status = 'active'
        msg = 'Carte activée.'
    card.save()
    Notification.objects.create(
        user=request.user,
        message=f'Carte •••• {card.card_number[-4:]} {card.status}.',
        type='confirm_transaction',
    )
    messages.success(request, msg)
    return redirect('cards')
