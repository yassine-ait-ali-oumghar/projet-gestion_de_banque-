from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Account, Transaction
from notifications.models import Notification
from decimal import Decimal, InvalidOperation
import random
import string


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
    accounts = Account.objects.filter(user=request.user)
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
        account = get_object_or_404(Account, id=account_id, user=request.user)
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
    accounts = Account.objects.filter(user=request.user)
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
        account = get_object_or_404(Account, id=account_id, user=request.user)
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
    accounts = Account.objects.filter(user=request.user)
    if request.method == 'POST':
        sender_id = request.POST.get('sender')
        receiver_number = request.POST.get('receiver')
        amount_str = request.POST.get('amount')
        try:
            amount = Decimal(amount_str).quantize(Decimal('0.01'))
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'Montant invalide.')
            return redirect('transfer')
        sender = get_object_or_404(Account, id=sender_id, user=request.user)
        try:
            receiver = Account.objects.get(account_number=receiver_number)
        except Account.DoesNotExist:
            messages.error(request, 'Compte destinataire introuvable.')
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
