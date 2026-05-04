from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """Extension du modèle User pour les informations supplémentaires."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Profil de {self.user.username}"
