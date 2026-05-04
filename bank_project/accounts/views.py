from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, ProfileForm
from .models import Profile
from notifications.models import Notification


def register_view(request):
    """Vue d'inscription d'un nouvel utilisateur."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            Notification.objects.create(
                user=user,
                message='Bienvenue chez NovaBank ! Votre compte a été créé avec succès.',
                type='welcome',
            )
            messages.success(request, 'Inscription réussie ! Bienvenue.')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Vue de connexion."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            Notification.objects.create(
                user=user,
                message=f'Connexion détectée à votre compte.',
                type='login_alert',
            )
            messages.success(request, 'Connexion réussie.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Identifiants invalides.')
    return render(request, 'accounts/login.html')


def logout_view(request):
    """Vue de déconnexion."""
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('home')


@login_required
def profile_view(request):
    """Vue du profil utilisateur."""
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            profile.phone = form.cleaned_data['phone']
            profile.address = form.cleaned_data['address']
            profile.save()
            messages.success(request, 'Profil mis à jour.')
            return redirect('profile')
    else:
        form = ProfileForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': profile.phone,
            'address': profile.address,
        })
    return render(request, 'accounts/profile.html', {'form': form, 'profile': profile})
