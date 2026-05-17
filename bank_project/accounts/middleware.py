from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect


class ActiveUserMiddleware:
    """
    Middleware qui vérifie que l'utilisateur connecté est toujours actif.
    Si l'utilisateur a été désactivé par un admin, il est déconnecté immédiatement
    avec un message explicite.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_active:
            logout(request)
            messages.error(
                request,
                'Votre compte a été suspendu. Contactez le support.',
            )
            return redirect('login')
        return self.get_response(request)
