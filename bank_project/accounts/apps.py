from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def _bootstrap_nova_admin(sender, app_config, **kwargs):
    if app_config.label != 'accounts':
        return
    if not getattr(settings, 'NOVA_ADMIN_AUTO_BOOTSTRAP', False):
        return
    from accounts.nova_admin_bootstrap import ensure_nova_admin_user

    level, msg = ensure_nova_admin_user(update_password=False)
    if level == 'success':
        import logging

        logging.getLogger('accounts').info('NOVA_ADMIN bootstrap: %s', msg)


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        post_migrate.connect(_bootstrap_nova_admin, dispatch_uid='nova_admin_post_migrate')
