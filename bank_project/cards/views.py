from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Card
from banking.models import Account, Transaction
from notifications.models import Notification
from decimal import Decimal, InvalidOperation
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
    accounts = Account.objects.filter(user=request.user, is_active=True)
    if not accounts.exists():
        messages.warning(request, 'Vous devez avoir un compte bancaire actif pour demander une carte.')
        return redirect('create_account')
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


@login_required
def card_payment(request):
    """Effectuer un paiement avec une carte bancaire."""
    user_accounts = Account.objects.filter(user=request.user)
    today = date.today()
    cards = Card.objects.filter(account__in=user_accounts, status='active').select_related('account')
    cards = [c for c in cards if c.expiration_date >= today]
    if not cards:
        messages.warning(request, 'Vous n\'avez aucune carte bancaire active. Veuillez en demander une.')
        return redirect('request_card')
    if request.method == 'POST':
        card_id = request.POST.get('card')
        amount_str = request.POST.get('amount')
        description = request.POST.get('description', 'Paiement')
        
        try:
            amount = Decimal(amount_str).quantize(Decimal('0.01'))
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'Montant invalide.')
            return redirect('card_payment')
        
        card = get_object_or_404(Card, id=card_id, account__in=user_accounts, status='active')
        if card.expiration_date < today:
            messages.error(request, 'Cette carte est expirée.')
            return redirect('card_payment')
        account = card.account
        
        if card.last_spending_date != today:
            card.daily_spent = Decimal('0.00')
            card.last_spending_date = today
        
        if (card.daily_spent + amount) > card.plafond:
            messages.error(request, f'Limite quotidienne dépassée ! Plafond: {card.plafond} MAD, Dépensé aujourd\'hui: {card.daily_spent} MAD.')
            return redirect('card_payment')
        
        if account.balance < amount:
            messages.error(request, 'Solde insuffisant sur le compte.')
            return redirect('card_payment')
        
        account.balance -= amount
        account.save()
        
        card.daily_spent += amount
        card.save()
        
        Transaction.objects.create(
            sender=account,
            amount=amount,
            type='card_payment',
            status='completed',
        )
        
        Notification.objects.create(
            user=request.user,
            message=f'Paiement de {amount} MAD effectué avec la carte •••• {card.card_number[-4:]}.',
            type='confirm_transaction',
        )
        
        messages.success(request, f'Paiement de {amount} MAD effectué avec succès.')
        return redirect('cards')
    
    return render(request, 'cards/card_payment.html', {'cards': cards})
