from django.db import models
from django.contrib.auth.models import User

class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    type = models.CharField(max_length=50) # e.g. Checking, Savings
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.account_number}"

class Transaction(models.Model):
    sender = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='sent_transactions', null=True, blank=True)
    receiver = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='received_transactions', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=50) # e.g. deposit, withdrawal, transfer
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='completed')

    def __str__(self):
        return f"{self.type} - {self.amount}"
