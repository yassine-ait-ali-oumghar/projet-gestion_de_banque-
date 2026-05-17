from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from banking.models import Account, Transaction
from notifications.models import Notification
from cards.models import Card
from datetime import datetime


@login_required
def dashboard_view(request):
    """Tableau de bord de l'utilisateur."""
    accounts = Account.objects.filter(user=request.user)
    total_balance = sum(a.balance for a in accounts)

    # Dernières transactions
    user_accounts = Account.objects.filter(user=request.user)
    recent_transactions = (
        Transaction.objects.filter(sender__in=user_accounts) |
        Transaction.objects.filter(receiver__in=user_accounts)
    ).order_by('-date')[:5]

    # Totals by type
    all_tx = (
        Transaction.objects.filter(sender__in=user_accounts) |
        Transaction.objects.filter(receiver__in=user_accounts)
    )
    total_deposits = all_tx.filter(type='deposit').aggregate(s=Sum('amount'))['s'] or 0
    total_withdrawals = all_tx.filter(type='withdrawal').aggregate(s=Sum('amount'))['s'] or 0
    total_transfers = all_tx.filter(type='transfer', sender__in=user_accounts).aggregate(s=Sum('amount'))['s'] or 0

    # Notifications non lues
    unread_notifications = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    # Card count
    from datetime import date as dt_date
    today = dt_date.today()
    card_count = Card.objects.filter(account__in=user_accounts, status='active').count()
    has_active_card = Card.objects.filter(
        account__in=user_accounts, status='active', expiration_date__gte=today
    ).exists()
    has_active_account = accounts.filter(is_active=True).exists()

    # Monthly data for chart (last 6 months)
    now = datetime.now()
    chart_labels = []
    chart_deposits = []
    chart_withdrawals = []
    months_fr = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
    for i in range(5, -1, -1):
        m = now.month - i
        y = now.year
        if m <= 0:
            m += 12
            y -= 1
        chart_labels.append(months_fr[m - 1])
        dep = all_tx.filter(type='deposit', date__year=y, date__month=m).aggregate(s=Sum('amount'))['s'] or 0
        wd = all_tx.filter(type='withdrawal', date__year=y, date__month=m).aggregate(s=Sum('amount'))['s'] or 0
        chart_deposits.append(float(dep))
        chart_withdrawals.append(float(wd))

    # Time-based greeting
    hour = now.hour
    if hour < 12:
        greeting = 'Bonjour'
    elif hour < 18:
        greeting = 'Bon après-midi'
    else:
        greeting = 'Bonsoir'

    context = {
        'accounts': accounts,
        'total_balance': total_balance,
        'recent_transactions': recent_transactions,
        'unread_notifications': unread_notifications,
        'num_accounts': accounts.count(),
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_transfers': total_transfers,
        'card_count': card_count,
        'has_active_card': has_active_card,
        'has_active_account': has_active_account,
        'greeting': greeting,
        'chart_labels': chart_labels,
        'chart_deposits': chart_deposits,
        'chart_withdrawals': chart_withdrawals,
    }
    return render(request, 'dashboard/dashboard.html', context)
