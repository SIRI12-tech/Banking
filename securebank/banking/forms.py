from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from captcha.fields import CaptchaField
from .models import Account, ContactMessage, Transaction, Bill

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    captcha = CaptchaField()

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class DepositForm(forms.ModelForm):
    to_account_number = forms.CharField(max_length=10, label="To Account Number")

    class Meta:
        model = Transaction
        fields = ['amount', 'description']

    def clean_to_account_number(self):
        account_number = self.cleaned_data['to_account_number']
        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            raise ValidationError("Invalid account number.")
        return account_number

class TransferForm(forms.ModelForm):
    from_account_number = forms.CharField(max_length=10, label="From Account Number")
    to_account_number = forms.CharField(max_length=10, label="To Account Number")

    class Meta:
        model = Transaction
        fields = ['amount', 'description']

    def clean_from_account_number(self):
        account_number = self.cleaned_data['from_account_number']
        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            raise ValidationError("Invalid account number.")
        return account_number

    def clean_to_account_number(self):
        account_number = self.cleaned_data['to_account_number']
        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            raise ValidationError("Invalid account number.")
        return account_number

    def clean(self):
        cleaned_data = super().clean()
        from_account_number = cleaned_data.get('from_account_number')
        to_account_number = cleaned_data.get('to_account_number')

        if from_account_number == to_account_number:
            raise ValidationError("You cannot transfer money to the same account.")

        return cleaned_data

class WithdrawalForm(forms.ModelForm):
    from_account_number = forms.CharField(max_length=10, label="From Account Number")

    class Meta:
        model = Transaction
        fields = ['amount', 'description']

    def clean_from_account_number(self):
        account_number = self.cleaned_data['from_account_number']
        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            raise ValidationError("Invalid account number.")
        return account_number

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'amount', 'description']

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount

class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['name', 'amount', 'due_date']

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount
    
class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }    