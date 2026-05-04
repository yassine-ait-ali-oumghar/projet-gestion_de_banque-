from django.db import models
from banking.models import Account

class Card(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='cards')
    card_number = models.CharField(max_length=16, unique=True)
    expiration_date = models.DateField()
    status = models.CharField(max_length=20, default='active')
    plafond = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Card {self.card_number} ({self.status})"
