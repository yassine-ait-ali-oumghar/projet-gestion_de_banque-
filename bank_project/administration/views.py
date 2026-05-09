from functools import partial

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from banking.models import Account, Transaction

User = get_user_model()

staff_only = partial(staff_member_required, login_url=settings.LOGIN_URL)

PAGE_SIZE_USERS = 20
PAGE_SIZE_ACCOUNTS = 20
PAGE_SIZE_TX = 40


def _nav_context():
    return {
        'adm_nav': [
            {'url_name': 'adm_dashboard', 'label': "Vue d'ensemble", 'icon': 'bi-grid-1x2'},
            {'url_name': 'adm_users', 'label': 'Utilisateurs', 'icon': 'bi-people'},
            {'url_name': 'adm_accounts', 'label': 'Comptes bancaires', 'icon': 'bi-wallet2'},
            {'url_name': 'adm_transactions', 'label': 'Transactions', 'icon': 'bi-arrow-left-right'},
            # Même comportement que les entrées ci-dessus : navigation dans cet onglet, pas target=_blank.
            {'url_name': 'admin:index', 'label': 'Django Admin (CRUD)', 'icon': 'bi-gear-fill'},
        ]
    }


@staff_only
def dashboard(request):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    agg_accounts = Account.objects.aggregate(
        total_balance=Sum('balance'),
        count=Count('id'),
        active_count=Count('id', filter=Q(is_active=True)),
    )

    tx_month = Transaction.objects.filter(date__gte=month_start)
    tx_volume_month = tx_month.aggregate(vol=Sum('amount'))['vol'] or 0
    tx_all_time = Transaction.objects.aggregate(vol=Sum('amount'))['vol'] or 0

    tx_by_type = list(
        Transaction.objects.values('type').annotate(cnt=Count('id')).order_by('-cnt')[:12]
    )

    context = {
        'user_total': User.objects.count(),
        'user_active': User.objects.filter(is_active=True).count(),
        'staff_count': User.objects.filter(is_staff=True).count(),
        'accounts_total': agg_accounts['count'] or 0,
        'accounts_active': agg_accounts['active_count'] or 0,
        'accounts_balance': agg_accounts['total_balance'] or 0,
        'tx_total': Transaction.objects.count(),
        'tx_volume_month': tx_volume_month,
        'tx_volume_all_time': tx_all_time,
        'tx_by_type': tx_by_type,
        'recent_transactions': Transaction.objects.order_by('-date')[:12],
        **_nav_context(),
        'adm_title': 'Supervision système',
    }
    return render(request, 'administration/dashboard.html', context)


@staff_only
def users_list(request):
    queryset = User.objects.all().order_by('-date_joined')
    q = (request.GET.get('q') or '').strip()
    if q:
        queryset = queryset.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )
    paginator = Paginator(queryset, PAGE_SIZE_USERS)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'q': q,
        **_nav_context(),
        'adm_title': 'Utilisateurs',
    }
    return render(request, 'administration/users.html', context)


@staff_only
def accounts_panel(request):
    queryset = Account.objects.select_related('user').order_by('-date_creation')
    q = (request.GET.get('q') or '').strip()
    if q:
        queryset = queryset.filter(
            Q(account_number__icontains=q)
            | Q(user__username__icontains=q)
            | Q(type__icontains=q)
        )
    status = request.GET.get('status')
    if status == 'active':
        queryset = queryset.filter(is_active=True)
    elif status == 'inactive':
        queryset = queryset.filter(is_active=False)
    paginator = Paginator(queryset, PAGE_SIZE_ACCOUNTS)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'q': q,
        'status': status or '',
        **_nav_context(),
        'adm_title': 'Comptes bancaires',
    }
    return render(request, 'administration/accounts.html', context)


@staff_only
def transactions_panel(request):
    queryset = Transaction.objects.select_related(
        'sender', 'receiver', 'sender__user', 'receiver__user'
    ).order_by('-date')
    tx_type = request.GET.get('type')
    if tx_type:
        queryset = queryset.filter(type=tx_type)
    q = (request.GET.get('q') or '').strip()
    if q:
        queryset = queryset.filter(Q(sender__account_number__icontains=q) | Q(receiver__account_number__icontains=q))
    paginator = Paginator(queryset, PAGE_SIZE_TX)
    page_obj = paginator.get_page(request.GET.get('page'))
    distinct_types = list(Transaction.objects.values_list('type', flat=True).distinct().order_by('type'))
    context = {
        'page_obj': page_obj,
        'tx_type': tx_type or '',
        'distinct_types': distinct_types,
        'q': q,
        **_nav_context(),
        'adm_title': 'Toutes les transactions',
    }
    return render(request, 'administration/transactions.html', context)


@staff_only
@require_POST
def toggle_user_active(request, pk):
    target = get_object_or_404(User, pk=pk)
    redirect_to = redirect('adm_users')

    if target.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas modifier votre propre statut depuis ce panneau.")
        return redirect_to

    if target.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Seuls les super-utilisateurs peuvent modifier ce compte.')
        return redirect_to

    if target.is_superuser and target.is_active:
        other_active_su = User.objects.filter(is_superuser=True, is_active=True).exclude(pk=target.pk).exists()
        if not other_active_su:
            messages.error(request, "Impossible de désactiver le dernier super-utilisateur actif.")
            return redirect_to

    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    state = 'activé' if target.is_active else 'désactivé'
    messages.success(request, f'Utilisateur « {target.username} » {state}.')
    return redirect_to


@staff_only
@require_POST
def toggle_account_active(request, pk):
    account = get_object_or_404(Account, pk=pk)
    account.is_active = not account.is_active
    account.save(update_fields=['is_active'])
    state = 'activé' if account.is_active else 'désactivé'
    messages.success(request, f'Compte « {account.account_number} » {state}.')
    return redirect('adm_accounts')
