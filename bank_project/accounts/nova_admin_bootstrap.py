"""Création du compte administrateur à partir de settings.NOVA_ADMIN_DEFAULT."""

from django.conf import settings
from django.contrib.auth import get_user_model


def ensure_nova_admin_user(*, update_password: bool = False) -> tuple[str, str]:
    """
    Retourne (niveau, message) avec niveau dans success, warning, error.
    """
    creds = getattr(settings, 'NOVA_ADMIN_DEFAULT', None)
    if not creds or not all(creds.get(k) for k in ('username', 'email', 'password')):
        return 'error', 'NOVA_ADMIN_DEFAULT est incomplet ou absent dans settings.'

    User = get_user_model()
    username = creds['username'].strip()
    email = creds['email'].strip()
    password = creds['password']

    user = User.objects.filter(username__iexact=username).first()
    if user is None:
        User.objects.create_superuser(username=username, email=email, password=password)
        return 'success', f"Superutilisateur « {username} » créé."

    if update_password:
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        return 'success', f"Compte « {username} » mis à jour (mot de passe et droits admin)."

    return 'warning', f"Un utilisateur « {username} » existe déjà — aucune modification (utilisez --reset)."
