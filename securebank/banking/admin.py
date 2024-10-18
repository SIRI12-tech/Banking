from django.contrib import admin, messages
from django.shortcuts import render
from .utils import send_notification
from .models import BlockedTransaction, ContactMessage, Notification
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Account, Transaction
from django import forms

class AccountInline(admin.StackedInline):
    model = Account
    can_delete = False
    verbose_name_plural = 'Account'

class UserAdmin(BaseUserAdmin):
    inlines = (AccountInline,)

class AddMoneyForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_number', 'balance', 'is_blocked')
    search_fields = ('user__username', 'account_number')
    readonly_fields = ('balance',)
    list_filter = ('is_blocked',)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(AccountAdmin, self).get_inline_instances(request, obj)

    def add_money(self, request, queryset):
        if 'apply' in request.POST:
            form = AddMoneyForm(request.POST)
            if form.is_valid():
                amount = form.cleaned_data['amount']
                updated = 0
                for account in queryset:
                    account.balance += amount
                    account.save()
                    Transaction.objects.create(
                        account=account,
                        transaction_type='DEPOSIT',
                        amount=amount,
                        description='Admin deposit'
                    )
                    updated += 1
                self.message_user(request, f"Added {amount} to {updated} accounts.")
                return None
        else:
            form = AddMoneyForm()

        return render(
            request,
            'admin/add_money.html',
            context={'accounts': queryset, 'form': form, 'title': 'Add money to accounts'}
        )

    add_money.short_description = "Add money to selected accounts"
    actions = ['add_money']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'transaction_type', 'amount', 'to_account', 'status', 'timestamp')
    list_filter = ('transaction_type', 'status')
    search_fields = ('account__user__username', 'to_account__user__username', 'reference_number')
    actions = ['approve_transactions', 'reject_transactions', 'block_transactions']
    
    def approve_transactions(self, request, queryset):
        for transaction in queryset.filter(status='PENDING'):
            transaction.status = 'APPROVED'
            transaction.save()
            if transaction.transaction_type == 'TRANSFER':
                transaction.to_account.balance += transaction.amount
                transaction.to_account.save()
            send_notification(transaction.account.user, f"Your {transaction.get_transaction_type_display().lower()} of ${transaction.amount} has been approved.")
        self.message_user(request, f"{queryset.filter(status='APPROVED').count()} transactions were approved and processed.")

    def reject_transactions(self, request, queryset):
        for transaction in queryset.filter(status='PENDING'):
            transaction.status = 'REJECTED'
            transaction.save()
            if transaction.transaction_type == 'TRANSFER':
                transaction.account.balance += transaction.amount
                transaction.account.save()
            send_notification(transaction.account.user, f"Your {transaction.get_transaction_type_display().lower()} of ${transaction.amount} has been rejected.")
        self.message_user(request, f"{queryset.filter(status='REJECTED').count()} transactions were rejected.")

    def block_transactions(self, request, queryset):
        for transaction in queryset.filter(status='PENDING'):
            transaction.status = 'BLOCKED'
            transaction.save()
            if transaction.transaction_type == 'TRANSFER':
                transaction.account.balance += transaction.amount
                transaction.account.save()
            BlockedTransaction.objects.create(
                account=transaction.account,
                transaction_type=transaction.transaction_type,
                reason="Blocked by admin"
            )
            send_notification(transaction.account.user, f"Your {transaction.get_transaction_type_display().lower()} of ${transaction.amount} has been blocked.")
        self.message_user(request, f"{queryset.filter(status='BLOCKED').count()} transactions were blocked.")
    
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    date_hierarchy = 'created_at'

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected messages as read"

    actions = [mark_as_read]

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'message')

@admin.register(BlockedTransaction)
class BlockedTransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'transaction_type', 'reason')
    list_filter = ('transaction_type',)
    search_fields = ('account__user__username',)