from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction as db_transaction
from .models import Card
from banking.models import Account, Transaction
from notifications.models import Notification
from decimal import Decimal, InvalidOperation
import random
from datetime import date
from dateutil.relativedelta import relativedelta

CARD_REQUEST_MIN_BALANCE = Decimal('500.00')
CARD_DAILY_LIMIT = Decimal('10000.00')


@login_required
def cards_list(request):
    """Liste des cartes bancaires de l'utilisateur."""
    user_accounts = Account.objects.filter(user=request.user)
    cards = Card.objects.filter(account__in=user_accounts).select_related('account')

    # Compute which accounts already have a card (active or inactive)
    accounts_with_card = set(
        Card.objects.filter(account__in=user_accounts).values_list('account_id', flat=True)
    )

    # Check if user has any active card (for card payment button state)
    today = date.today()
    has_active_card = Card.objects.filter(
        account__in=user_accounts,
        status='active',
        expiration_date__gte=today,
    ).exists()

    return render(request, 'cards/cards.html', {
        'cards': cards,
        'accounts': user_accounts,
        'has_active_card': has_active_card,
        'accounts_with_card': accounts_with_card,
    })


@login_required
def request_card(request):
    """Demander une nouvelle carte bancaire."""
    accounts = Account.objects.filter(user=request.user, is_active=True)
    if not accounts.exists():
        messages.warning(request, 'Vous devez avoir un compte bancaire actif pour demander une carte.')
        return redirect('create_account')

    # Filter out accounts that already have a card
    accounts_with_card = set(
        Card.objects.filter(account__in=accounts).values_list('account_id', flat=True)
    )
    eligible_accounts = [acc for acc in accounts if acc.id not in accounts_with_card]

    if request.method == 'POST':
        account_id = request.POST.get('account')
        account = get_object_or_404(Account, id=account_id, user=request.user, is_active=True)

        # Rule: account must not already have a card
        existing_card = Card.objects.filter(account=account).first()
        if existing_card:
            messages.error(
                request,
                f'Le compte {account.account_number} possède déjà une carte '
                f'(•••• {existing_card.card_number[-4:]}). '
                f'Supprimez-la d\'abord avant d\'en demander une nouvelle.'
            )
            return redirect('cards')

        # Rule: minimum balance required
        if account.balance < CARD_REQUEST_MIN_BALANCE:
            messages.error(
                request,
                f'Solde insuffisant. Un solde minimum de {CARD_REQUEST_MIN_BALANCE} MAD '
                f'est requis pour demander une carte. Solde actuel : {account.balance:.2f} MAD.'
            )
            return redirect('request_card')

        card_number = ''.join([str(random.randint(0, 9)) for _ in range(16)])
        expiry = date.today() + relativedelta(years=3)
        card = Card.objects.create(
            account=account,
            card_number=card_number,
            expiration_date=expiry,
            status='active',
            plafond=CARD_DAILY_LIMIT,
        )
        Notification.objects.create(
            user=request.user,
            message=f'Carte bancaire demandée et activée pour le compte {account.account_number} (•••• {card.card_number[-4:]}).',
            type='card_requested',
        )
        messages.success(request, 'Carte bancaire créée et activée avec succès.')
        return redirect('cards')

    return render(request, 'cards/request_card.html', {
        'accounts': eligible_accounts,
        'min_balance': CARD_REQUEST_MIN_BALANCE,
        'accounts_with_card': accounts_with_card,
    })


@login_required
def toggle_card(request, card_id):
    """Activer/Désactiver une carte bancaire."""
    user_accounts = Account.objects.filter(user=request.user)
    card = get_object_or_404(Card, id=card_id, account__in=user_accounts)
    if card.status == 'active':
        card.status = 'inactive'
        card.save()
        msg = 'Carte désactivée.'
        Notification.objects.create(
            user=request.user,
            message=f'Carte •••• {card.card_number[-4:]} désactivée.',
            type='card_deactivated',
        )
    else:
        card.status = 'active'
        card.save()
        msg = 'Carte activée.'
        Notification.objects.create(
            user=request.user,
            message=f'Carte •••• {card.card_number[-4:]} activée.',
            type='card_activated',
        )
    messages.success(request, msg)
    return redirect('cards')


@login_required
def delete_card(request, card_id):
    """Supprimer une carte bancaire."""
    user_accounts = Account.objects.filter(user=request.user)
    card = get_object_or_404(Card, id=card_id, account__in=user_accounts)
    if request.method == 'POST':
        card_last4 = card.card_number[-4:]
        card.delete()
        messages.success(request, f'Carte •••• {card_last4} supprimée.')
        Notification.objects.create(
            user=request.user,
            message=f'Carte •••• {card_last4} supprimée définitivement.',
            type='card_deleted',
        )
    return redirect('cards')


@login_required
def card_payment(request):
    """Effectuer un paiement avec une carte bancaire."""
    user_accounts = Account.objects.filter(user=request.user)
    today = date.today()
    cards = Card.objects.filter(account__in=user_accounts, status='active').select_related('account')
    cards = [c for c in cards if c.expiration_date >= today]

    if not cards:
        messages.warning(
            request,
            'Vous devez d\'abord demander et activer une carte bancaire.'
        )
        return redirect('cards')

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

        # Atomic: lock card and account together
        with db_transaction.atomic():
            card = Card.objects.select_for_update().get(
                id=card_id, account__in=user_accounts
            )

            # Re-check card is active (deactivated card blocks immediately)
            if card.status != 'active':
                messages.error(request, 'Cette carte est désactivée. Le paiement est refusé.')
                return redirect('card_payment')

            if card.expiration_date < today:
                messages.error(request, 'Cette carte est expirée.')
                return redirect('card_payment')

            account = Account.objects.select_for_update().get(id=card.account_id)

            # Check account is active
            if not account.is_active:
                messages.error(request, 'Ce compte est inactif. Contactez le support.')
                return redirect('card_payment')

            # Reset daily spending if new day
            if card.last_spending_date != today:
                card.daily_spent = Decimal('0.00')
                card.last_spending_date = today

            # Check card daily limit
            if (card.daily_spent + amount) > card.plafond:
                remaining = card.plafond - card.daily_spent
                if remaining <= 0:
                    messages.error(request, 'Limite journalière atteinte. Réessayez demain.')
                else:
                    messages.error(
                        request,
                        f'Limite quotidienne dépassée ! Plafond: {card.plafond} MAD, '
                        f'Dépensé aujourd\'hui: {card.daily_spent} MAD. '
                        f'Restant: {remaining:.2f} MAD.'
                    )
                return redirect('card_payment')

            # Check account balance
            if account.balance < amount:
                messages.error(request, 'Solde insuffisant sur le compte lié.')
                return redirect('card_payment')

            # Check the payment wouldn't bring balance below 0
            if (account.balance - amount) < Decimal('0.00'):
                messages.error(request, 'Le paiement amènerait le solde en dessous de 0. Opération refusée.')
                return redirect('card_payment')

            # All checks passed — execute
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

            label = description or 'Paiement par carte'
            Notification.objects.create(
                user=request.user,
                message=f'Paiement de {amount} MAD effectué avec la carte •••• {card.card_number[-4:]} — {label}.',
                type='card_payment',
            )

        messages.success(request, f'Paiement de {amount} MAD effectué avec succès.')
        return redirect('cards')

    return render(request, 'cards/card_payment.html', {'cards': cards})
