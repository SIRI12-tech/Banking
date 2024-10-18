from django.utils import timezone
from datetime import timedelta
from .models import Transaction
from .utils import send_notification

def cleanup_old_pending_transactions():
    thirty_days_ago = timezone.now() - timedelta(days=30)
    old_pending_transactions = Transaction.objects.filter(status='PENDING', timestamp__lt=thirty_days_ago)
    
    for transaction in old_pending_transactions:
        transaction.status = 'REJECTED'
        transaction.save()
        
        if transaction.transaction_type == 'TRANSFER':
            transaction.account.balance += transaction.amount
            transaction.account.save()
        
        send_notification(transaction.account.user, f"Your pending {transaction.get_transaction_type_display().lower()} of ${transaction.amount} has been automatically rejected due to inactivity.")

    print(f"Cleaned up {old_pending_transactions.count()} old pending transactions.")