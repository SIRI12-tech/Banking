import random
import string
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

def generate_account_number():
    return ''.join(random.choices(string.digits, k=10))

class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=10, unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, null=True, blank=True)
    is_blocked = models.BooleanField(default=False)

    @classmethod
    def generate_account_number(cls):
        while True:
            account_number = ''.join([str(random.randint(0, 9)) for _ in range(10)])
            if not cls.objects.filter(account_number=account_number).exists():
                return account_number

    def __str__(self):
        return f"{self.user.username}'s account ({self.account_number})"
    
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('TRANSFER', 'Transfer'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('BLOCKED', 'Blocked'),
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    to_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_transfers')
    reference_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"{self.transaction_type} of {self.amount} for {self.account.user.username} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))
        super().save(*args, **kwargs)

class BlockedTransaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=Transaction.TRANSACTION_TYPES)
    reason = models.TextField()

    def __str__(self):
        return f"Blocked {self.transaction_type} for {self.account.user.username}"

class Bill(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='bills')
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - ${self.amount} due on {self.due_date}"
    
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.subject} - {self.name}"

    class Meta:
        ordering = ['-created_at']
        
        
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"        

class ChatRoom(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_bot = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username if self.user else 'Bot'}: {self.message[:50]}"

class ChatQueue(models.Model):
    room = models.OneToOneField(ChatRoom, on_delete=models.CASCADE, related_name='queue')
    users = models.ManyToManyField(User, related_name='chat_queues')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Queue for {self.room.name}"