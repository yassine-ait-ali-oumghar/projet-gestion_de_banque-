from django.core.management.base import BaseCommand

from accounts.nova_admin_bootstrap import ensure_nova_admin_user


class Command(BaseCommand):
    help = 'Crée le superutilisateur NovaBank défini dans settings.NOVA_ADMIN_DEFAULT.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Réinitialise le mot de passe, l’e-mail et les droits admin pour ce compte.',
        )

    def handle(self, *args, **options):
        level, msg = ensure_nova_admin_user(update_password=bool(options['reset']))
        styles = {'success': self.style.SUCCESS, 'warning': self.style.WARNING, 'error': self.style.ERROR}
        self.stdout.write(styles[level](msg))
        from django.conf import settings

        creds = getattr(settings, 'NOVA_ADMIN_DEFAULT', {})
        if level == 'success' or level == 'warning':
            self.stdout.write('')
            self.stdout.write('Connexion NovaBank (/accounts/login/) ou panneau /administration/ :')
            self.stdout.write(f"  Username : {creds.get('username', '?')}")
            self.stdout.write(f"  Email    : {creds.get('email', '?')} (connexion aussi avec cet e-mail)")
            self.stdout.write(f"  Mot de passe : {creds.get('password', '?')}")
