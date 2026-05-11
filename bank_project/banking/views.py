from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from .models import Account, Transaction
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

DEPOSIT_MIN = Decimal('100.00')
DEPOSIT_MAX = Decimal('50000.00')
WITHDRAW_MIN = Decimal('50.00')
WITHDRAW_MAX = Decimal('3000.00')
WITHDRAW_DAILY_LIMIT = Decimal('10000.00')
TRANSFER_MIN = Decimal('10.00')
TRANSFER_MAX = Decimal('10000.00')
TRANSFER_DAILY_LIMIT = Decimal('20000.00')


def _daily_total(account, tx_type):
    today = date.today()
    result = Transaction.objects.filter(
        sender=account, type=tx_type, date__date=today
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
            balance=0.00,
            type=account_type,
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
        account = get_object_or_404(Account, id=account_id, user=request.user, is_active=True)
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
    return render(request, 'banking/deposit.html', {'accounts': accounts})


@login_required
def withdraw(request):
    """Retrait d'argent d'un compte."""
    accounts = Account.objects.filter(user=request.user, is_active=True)
    if not accounts.exists():
        messages.warning(request, 'Vous devez d\'abord créer un compte bancaire avant d\'effectuer un retrait.')
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
            return redirect('withdraw')
        if amount < WITHDRAW_MIN:
            messages.error(request, f'Le montant minimum de retrait est de {WITHDRAW_MIN} MAD.')
            return redirect('withdraw')
        if amount > WITHDRAW_MAX:
            messages.error(request, f'Le montant maximum de retrait est de {WITHDRAW_MAX} MAD par opération.')
            return redirect('withdraw')
        account = get_object_or_404(Account, id=account_id, user=request.user, is_active=True)
        daily_withdrawn = _daily_total(account, 'withdrawal')
        if daily_withdrawn + amount > WITHDRAW_DAILY_LIMIT:
            remaining = WITHDRAW_DAILY_LIMIT - daily_withdrawn
            messages.error(request, f'Plafond journalier de retrait atteint ({WITHDRAW_DAILY_LIMIT} MAD/jour). Il vous reste {remaining:.2f} MAD disponibles aujourd\'hui.')
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
    return render(request, 'banking/withdraw.html', {'accounts': accounts})


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
        sender = get_object_or_404(Account, id=sender_id, user=request.user, is_active=True)
        if sender.account_number == receiver_number:
            messages.error(request, 'Vous ne pouvez pas effectuer un virement vers le même compte.')
            return redirect('transfer')
        daily_transferred = _daily_total(sender, 'transfer')
        if daily_transferred + amount > TRANSFER_DAILY_LIMIT:
            remaining = TRANSFER_DAILY_LIMIT - daily_transferred
            messages.error(request, f'Plafond journalier de virement atteint ({TRANSFER_DAILY_LIMIT} MAD/jour). Il vous reste {remaining:.2f} MAD disponibles aujourd\'hui.')
            return redirect('transfer')
        try:
            receiver = Account.objects.get(account_number=receiver_number)
        except Account.DoesNotExist:
            messages.error(request, 'Compte destinataire introuvable.')
            return redirect('transfer')
        if not receiver.is_active:
            messages.error(request, 'Ce compte destinataire est désactivé.')
            return redirect('transfer')
        if sender.balance < amount:
            messages.error(request, 'Solde insuffisant.')
            return redirect('transfer')
        sender.balance -= amount
        sender.save()
        receiver.balance += amount
        receiver.save()
        Transaction.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount,
            type='transfer',
            status='completed',
        )
        Notification.objects.create(
            user=request.user,
            message=f'Virement de {amount} MAD de {sender.account_number} vers {receiver.account_number}.',
            type='confirm_transaction',
        )
        # Notify the receiver user if different
        if receiver.user != request.user:
            Notification.objects.create(
                user=receiver.user,
                message=f'Vous avez reçu un virement de {amount} MAD sur {receiver.account_number}.',
                type='confirm_transaction',
            )
        messages.success(request, f'Virement de {amount} MAD effectué.')
        return redirect('accounts_list')
    return render(request, 'banking/transfer.html', {'accounts': accounts})


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