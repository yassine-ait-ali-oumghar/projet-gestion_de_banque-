from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from .models import Account, Transaction
from cards.models import Card
from notifications.models import Notification
from decimal import Decimal, InvalidOperation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import random
import re
import string
from reportlab.lib.utils import ImageReader
from django.conf import settings
import os
from datetime import datetime, date
from io import BytesIO
from django.template.loader import render_to_string
try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

# ---------------------------------------------------------------------------
# Limites réglementaires NovaBank
# ---------------------------------------------------------------------------
DEPOSIT_MIN = Decimal('10.00')
DEPOSIT_MAX = Decimal('100000.00')
WITHDRAW_MIN = Decimal('20.00')
WITHDRAW_MAX = Decimal('10000.00')
WITHDRAW_DAILY_LIMIT = Decimal('20000.00')
TRANSFER_MIN = Decimal('10.00')
TRANSFER_MAX = Decimal('10000.00')
TRANSFER_DAILY_LIMIT = Decimal('20000.00')
SAVINGS_MIN_BALANCE = Decimal('100.00')
CARD_REQUEST_MIN_BALANCE = Decimal('500.00')


def _daily_total_for_account(account, tx_type):
    """Total journalier pour un compte donné et un type de transaction."""
    today = date.today()
    result = Transaction.objects.filter(
        sender=account, type=tx_type, date__date=today
    ).aggregate(total=Sum('amount'))['total']
    return result or Decimal('0.00')


def _daily_total_all_accounts(user, tx_type):
    """Total journalier GLOBAL (tous comptes) pour un utilisateur et un type."""
    today = date.today()
    user_accounts = Account.objects.filter(user=user)
    result = Transaction.objects.filter(
        sender__in=user_accounts, type=tx_type, date__date=today
    ).aggregate(total=Sum('amount'))['total']
    return result or Decimal('0.00')


def _generate_account_number():
    """Génère un numéro de compte unique."""
    return 'NB' + ''.join(random.choices(string.digits, k=10))


@login_required
def accounts_list(request):
    """Liste des comptes bancaires de l'utilisateur."""
    accounts = Account.objects.filter(user=request.user).order_by('-date_creation')
    total_balance = sum(a.balance for a in accounts)
    return render(request, 'banking/accounts.html', {
        'accounts': accounts,
        'total_balance': total_balance,
    })


@login_required
def create_account(request):
    """Création d'un nouveau compte bancaire."""
    if request.method == 'POST':
        account_type = request.POST.get('type', 'Courant')
        account = Account.objects.create(
            user=request.user,
            account_number=_generate_account_number(),
            balance=Decimal('0.00'),
            type=account_type,
            is_active=True,
        )
        Notification.objects.create(
            user=request.user,
            message=f'Nouveau compte {account_type} créé : {account.account_number}',
            type='account_created',
        )
        messages.success(request, f'Compte {account.account_number} créé avec succès.')
        return redirect('accounts_list')
    return render(request, 'banking/create_account.html')


@login_required
def onboarding_view(request):
    """Page d'accueil pour les nouveaux utilisateurs — création de compte + carte."""
    # If user already has accounts, skip onboarding
    if Account.objects.filter(user=request.user).exists():
        return redirect('dashboard')

    if request.method == 'POST':
        account_type = request.POST.get('account_type', 'Courant')
        action = request.POST.get('action', 'create_without_card')

        # Create the bank account
        account = Account.objects.create(
            user=request.user,
            account_number=_generate_account_number(),
            balance=Decimal('0.00'),
            type=account_type,
            is_active=True,
        )
        Notification.objects.create(
            user=request.user,
            message=f'Nouveau compte {account_type} créé : {account.account_number}',
            type='account_created',
        )

        card = None
        if action == 'create_with_card':
            from dateutil.relativedelta import relativedelta
            card_number = ''.join([str(random.randint(0, 9)) for _ in range(16)])
            expiry = date.today() + relativedelta(years=3)
            card = Card.objects.create(
                account=account,
                card_number=card_number,
                expiration_date=expiry,
                status='active',
                plafond=Decimal('10000.00'),
            )
            Notification.objects.create(
                user=request.user,
                message=f'Carte bancaire activée pour le compte {account.account_number} (•••• {card.card_number[-4:]}).',
                type='card_requested',
            )

        messages.success(request, f'Compte {account.account_number} créé avec succès !')
        # Redirect to the first deposit page
        return redirect('first_deposit', account_id=account.id)

    return render(request, 'banking/onboarding.html')


@login_required
def first_deposit_view(request, account_id):
    """Page de premier dépôt pour les nouveaux utilisateurs."""
    account = get_object_or_404(Account, id=account_id, user=request.user, is_active=True)
    card = Card.objects.filter(account=account).first()

    if request.method == 'POST':
        amount_str = request.POST.get('amount')
        try:
            amount = Decimal(amount_str).quantize(Decimal('0.01'))
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'Montant invalide.')
            return redirect('first_deposit', account_id=account.id)
        if amount < DEPOSIT_MIN:
            messages.error(request, f'Le montant minimum de dépôt est de {DEPOSIT_MIN} MAD.')
            return redirect('first_deposit', account_id=account.id)
        if amount > DEPOSIT_MAX:
            messages.error(request, f'Le montant maximum de dépôt est de {DEPOSIT_MAX} MAD.')
            return redirect('first_deposit', account_id=account.id)

        with db_transaction.atomic():
            acc = Account.objects.select_for_update().get(id=account.id)
            acc.balance += amount
            acc.save()
            Transaction.objects.create(
                receiver=acc,
                amount=amount,
                type='deposit',
                status='completed',
            )
            Notification.objects.create(
                user=request.user,
                message=f'Premier dépôt de {amount} MAD sur le compte {acc.account_number}. Bienvenue !',
                type='confirm_transaction',
            )
        messages.success(request, f'{amount} MAD déposés sur {account.account_number}. Votre espace bancaire est prêt !')
        return redirect('dashboard')

    return render(request, 'banking/first_deposit.html', {
        'account': account,
        'card': card,
    })


@login_required
def delete_account(request, pk):
    """Suppression d'un compte bancaire — solde doit être 0."""
    account = get_object_or_404(Account, pk=pk, user=request.user)
    if request.method == 'POST':
        if account.balance > Decimal('0.00'):
            messages.error(
                request,
                f'Impossible de supprimer le compte {account.account_number} : '
                f'le solde est de {account.balance} MAD. Vous devez d\'abord vider le compte.'
            )
            return redirect('accounts_list')
        account_number = account.account_number
        account.delete()
        Notification.objects.create(
            user=request.user,
            message=f'Compte {account_number} supprimé.',
            type='account_deleted',
        )
        messages.success(request, f'Compte {account_number} supprimé avec succès.')
    return redirect('accounts_list')


@login_required
def deposit(request):
    """Dépôt d'argent sur un compte."""
    accounts = Account.objects.filter(user=request.user, is_active=True)
    if not accounts.exists():
        messages.warning(request, 'Vous devez d\'abord créer un compte bancaire avant d\'effectuer un dépôt.')
        return redirect('create_account')
    if request.method == 'POST':
        account_id = request.POST.get('account')
        amount_str = request.POST.get('amount')
        try:
            amount = Decimal(amount_str).quantize(Decimal('0.01'))
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'Montant invalide.')
            return redirect('deposit')
        if amount < DEPOSIT_MIN:
            messages.error(request, f'Le montant minimum de dépôt est de {DEPOSIT_MIN} MAD.')
            return redirect('deposit')
        if amount > DEPOSIT_MAX:
            messages.error(request, f'Le montant maximum de dépôt est de {DEPOSIT_MAX} MAD par opération.')
            return redirect('deposit')

        # Atomic: lock the account row before modifying balance
        with db_transaction.atomic():
            account = Account.objects.select_for_update().get(id=account_id, user=request.user, is_active=True)
            account.balance += amount
            account.save()
            Transaction.objects.create(
                receiver=account,
                amount=amount,
                type='deposit',
                status='completed',
            )
            Notification.objects.create(
                user=request.user,
                message=f'Dépôt de {amount} MAD effectué sur le compte {account.account_number}.',
                type='confirm_transaction',
            )
        messages.success(request, f'{amount} MAD déposés sur {account.account_number}.')
        return redirect('accounts_list')
    return render(request, 'banking/deposit.html', {
        'accounts': accounts,
        'deposit_min': DEPOSIT_MIN,
        'deposit_max': DEPOSIT_MAX,
    })


@login_required
def withdraw(request):
    """Retrait d'argent d'un compte. Nécessite un compte ET une carte active."""
    accounts = Account.objects.filter(user=request.user, is_active=True)
    if not accounts.exists():
        messages.warning(request, 'Vous devez d\'abord créer un compte bancaire avant d\'effectuer un retrait.')
        return redirect('create_account')

    # RULE: Withdrawal requires an active card
    user_accounts = Account.objects.filter(user=request.user)
    has_active_card = Card.objects.filter(
        account__in=user_accounts,
        status='active',
        expiration_date__gte=date.today(),
    ).exists()
    if not has_active_card:
        messages.warning(
            request,
            'Vous devez posséder une carte bancaire active pour effectuer un retrait. '
            'Rendez-vous dans la section Cartes pour en demander une.'
        )
        return redirect('request_card')
    if request.method == 'POST':
        account_id = request.POST.get('account')
        amount_str = request.POST.get('amount')
        try:
            amount = Decimal(amount_str).quantize(Decimal('0.01'))
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'Montant invalide.')
            return redirect('withdraw')
        if amount < WITHDRAW_MIN:
            messages.error(request, f'Le montant minimum de retrait est de {WITHDRAW_MIN} MAD.')
            return redirect('withdraw')
        if amount > WITHDRAW_MAX:
            messages.error(request, f'Le montant maximum de retrait est de {WITHDRAW_MAX} MAD par opération.')
            return redirect('withdraw')

        # Atomic: lock the account and validate all constraints
        with db_transaction.atomic():
            account = Account.objects.select_for_update().get(id=account_id, user=request.user, is_active=True)

            if not account.is_active:
                messages.error(request, 'Ce compte est inactif. Contactez le support.')
                return redirect('withdraw')

            # Daily withdrawal cap across ALL user accounts
            daily_withdrawn = _daily_total_all_accounts(request.user, 'withdrawal')
            if daily_withdrawn + amount > WITHDRAW_DAILY_LIMIT:
                remaining = WITHDRAW_DAILY_LIMIT - daily_withdrawn
                if remaining <= 0:
                    messages.error(request, 'Limite journalière atteinte. Réessayez demain.')
                else:
                    messages.error(request, f'Plafond journalier de retrait atteint ({WITHDRAW_DAILY_LIMIT} MAD/jour). Il vous reste {remaining:.2f} MAD disponibles aujourd\'hui.')
                return redirect('withdraw')

            # Savings account: must keep minimum balance
            if account.type == 'Épargne':
                if (account.balance - amount) < SAVINGS_MIN_BALANCE:
                    messages.error(
                        request,
                        f'Compte Épargne : un solde minimum de {SAVINGS_MIN_BALANCE} MAD doit être maintenu. '
                        f'Retrait maximum possible : {account.balance - SAVINGS_MIN_BALANCE:.2f} MAD.'
                    )
                    return redirect('withdraw')

            if account.balance < amount:
                messages.error(request, 'Solde insuffisant.')
                return redirect('withdraw')

            account.balance -= amount
            account.save()
            Transaction.objects.create(
                sender=account,
                amount=amount,
                type='withdrawal',
                status='completed',
            )
            Notification.objects.create(
                user=request.user,
                message=f'Retrait de {amount} MAD effectué depuis le compte {account.account_number}.',
                type='confirm_transaction',
            )
        messages.success(request, f'{amount} MAD retirés de {account.account_number}.')
        return redirect('accounts_list')

    # Pre-compute daily remaining for template
    daily_withdrawn = _daily_total_all_accounts(request.user, 'withdrawal')
    daily_remaining = max(WITHDRAW_DAILY_LIMIT - daily_withdrawn, Decimal('0.00'))

    return render(request, 'banking/withdraw.html', {
        'accounts': accounts,
        'withdraw_min': WITHDRAW_MIN,
        'withdraw_max': WITHDRAW_MAX,
        'daily_limit': WITHDRAW_DAILY_LIMIT,
        'daily_remaining': daily_remaining,
    })


@login_required
def transfer(request):
    """Virement entre comptes."""
    accounts = Account.objects.filter(user=request.user, is_active=True)
    if not accounts.exists():
        messages.warning(request, 'Vous devez d\'abord créer un compte bancaire avant d\'effectuer un virement.')
        return redirect('create_account')
    if request.method == 'POST':
        sender_id = request.POST.get('sender')
        receiver_number = (request.POST.get('receiver') or '').strip().upper()
        amount_str = request.POST.get('amount')

        account_pattern = re.compile(r'^[A-Z]{2}\d+$')
        if not receiver_number or not account_pattern.match(receiver_number):
            messages.error(request, 'Format de compte invalide. Doit commencer par 2 lettres majuscules suivies de chiffres (ex: NB1234567890).')
            return redirect('transfer')

        try:
            amount = Decimal(amount_str).quantize(Decimal('0.01'))
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'Montant invalide.')
            return redirect('transfer')
        if amount < TRANSFER_MIN:
            messages.error(request, f'Le montant minimum de virement est de {TRANSFER_MIN} MAD.')
            return redirect('transfer')
        if amount > TRANSFER_MAX:
            messages.error(request, f'Le montant maximum de virement est de {TRANSFER_MAX} MAD par opération.')
            return redirect('transfer')

        # Validate destination exists before acquiring locks
        try:
            receiver_check = Account.objects.get(account_number=receiver_number)
        except Account.DoesNotExist:
            messages.error(request, 'Compte destinataire introuvable.')
            return redirect('transfer')
        if not receiver_check.is_active:
            messages.error(request, 'Ce compte destinataire est inactif. Contactez le support.')
            return redirect('transfer')

        # Atomic with row-level locking for both accounts
        with db_transaction.atomic():
            sender = Account.objects.select_for_update().get(id=sender_id, user=request.user, is_active=True)

            if not sender.is_active:
                messages.error(request, 'Ce compte est inactif. Contactez le support.')
                return redirect('transfer')

            # Daily transfer cap
            daily_transferred = _daily_total_all_accounts(request.user, 'transfer')
            if daily_transferred + amount > TRANSFER_DAILY_LIMIT:
                remaining = TRANSFER_DAILY_LIMIT - daily_transferred
                if remaining <= 0:
                    messages.error(request, 'Limite journalière atteinte. Réessayez demain.')
                else:
                    messages.error(request, f'Plafond journalier de virement atteint ({TRANSFER_DAILY_LIMIT} MAD/jour). Il vous reste {remaining:.2f} MAD disponibles aujourd\'hui.')
                return redirect('transfer')

            # Savings: must keep minimum balance
            if sender.type == 'Épargne':
                if (sender.balance - amount) < SAVINGS_MIN_BALANCE:
                    messages.error(
                        request,
                        f'Compte Épargne : un solde minimum de {SAVINGS_MIN_BALANCE} MAD doit être maintenu. '
                        f'Virement maximum possible : {sender.balance - SAVINGS_MIN_BALANCE:.2f} MAD.'
                    )
                    return redirect('transfer')

            if sender.balance < amount:
                messages.error(request, 'Solde insuffisant.')
                return redirect('transfer')

            receiver = Account.objects.select_for_update().get(account_number=receiver_number)

            # Determine transfer type label
            is_self_transfer = (sender.account_number == receiver_number)
            is_internal = (receiver.user == request.user) and not is_self_transfer

            sender.balance -= amount
            sender.save()
            receiver.balance += amount
            receiver.save()

            # Determine description label
            if is_self_transfer:
                transfer_label = 'Virement interne (même compte)'
            elif is_internal:
                transfer_label = 'Virement interne'
            else:
                transfer_label = 'Virement'

            Transaction.objects.create(
                sender=sender,
                receiver=receiver,
                amount=amount,
                type='transfer',
                status='completed',
            )

            # Notification for sender
            sender_msg = f'{transfer_label} de {amount} MAD de {sender.account_number} vers {receiver.account_number}.'
            Notification.objects.create(
                user=request.user,
                message=sender_msg,
                type='confirm_transaction',
            )
            # Notification for receiver (if different user)
            if receiver.user != request.user:
                Notification.objects.create(
                    user=receiver.user,
                    message=f'Vous avez reçu un virement de {amount} MAD sur {receiver.account_number} depuis {sender.account_number} le {date.today().strftime("%d/%m/%Y")}.',
                    type='confirm_transaction',
                )

        messages.success(request, f'{transfer_label} de {amount} MAD effectué.')
        return redirect('accounts_list')

    # Pre-compute daily remaining for template
    daily_transferred = _daily_total_all_accounts(request.user, 'transfer')
    daily_remaining = max(TRANSFER_DAILY_LIMIT - daily_transferred, Decimal('0.00'))

    return render(request, 'banking/transfer.html', {
        'accounts': accounts,
        'transfer_min': TRANSFER_MIN,
        'transfer_max': TRANSFER_MAX,
        'daily_limit': TRANSFER_DAILY_LIMIT,
        'daily_remaining': daily_remaining,
    })


@login_required
def transactions_list(request):
    """Historique des transactions de l'utilisateur."""
    user_accounts = Account.objects.filter(user=request.user)
    transactions = Transaction.objects.filter(
        sender__in=user_accounts
    ) | Transaction.objects.filter(
        receiver__in=user_accounts
    )
    transactions = transactions.order_by('-date')

    # Filtrage par type
    tx_type = request.GET.get('type')
    if tx_type:
        transactions = transactions.filter(type=tx_type)

    return render(request, 'banking/transactions.html', {
        'transactions': transactions,
        'tx_type': tx_type,
    })


@login_required
def export_transactions_pdf(request):
    """Exporte les transactions de l'utilisateur en PDF Premium avec HTML/CSS."""
    user_accounts = Account.objects.filter(user=request.user)
    transactions = Transaction.objects.filter(
        Q(sender__in=user_accounts) |
        Q(receiver__in=user_accounts)
    ).order_by('-date')

    total = sum(tx.amount for tx in transactions)
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")
    logo_path = os.path.join(settings.BASE_DIR, 'cachet_officiel_transparent.png')

    context = {
        'transactions': transactions,
        'total': total,
        'user_name': request.user.get_full_name() or request.user.username,
        'current_date': current_date,
        'logo_path': logo_path,
    }

    html = render_to_string('banking/report_pdf.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="NovaBank_Report.pdf"'

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)

    if pisa_status.err:
        return HttpResponse('Erreur lors de la génération du PDF', status=500)

    response.write(buffer.getvalue())
    return response