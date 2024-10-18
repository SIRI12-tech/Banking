from django.http import JsonResponse
from django.utils import timezone
import random
from django.db.models import Sum
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import viewsets
from django.db import transaction as db_transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Account, BlockedTransaction, Notification, Transaction, Bill
from .forms import ContactForm, CustomUserCreationForm, DepositForm, TransactionForm, TransferForm, WithdrawalForm
from .serializers import AccountSerializer, TransactionSerializer
from django.contrib.auth import authenticate, login as auth_login
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.crypto import get_random_string

def generate_account_number():
    return ''.join(random.choices(string.digits, k=10))

def create_account_if_not_exists(user):
    try:
        return Account.objects.get(user=user)
    except Account.DoesNotExist:
        account_number = generate_account_number()
        return Account.objects.create(user=user, account_number=account_number)

def home(request):
    return render(request, 'banking/home.html')

def about(request):
    return render(request, 'banking/about.html')

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save()
            
            # Send email to admin
            subject = f"New contact message: {contact_message.subject}"
            message = f"Name: {contact_message.name}\nEmail: {contact_message.email}\n\nMessage:\n{contact_message.message}"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [settings.ADMIN_EMAIL]
            
            send_mail(subject, message, from_email, recipient_list)
            
            messages.success(request, 'Your message has been sent. We will get back to you soon.')
            return redirect('contact')
    else:
        form = ContactForm()
    
    return render(request, 'banking/contact.html', {'form': form})

def privacy_policy(request):
    return render(request, 'banking/privacy_policy.html')

@ensure_csrf_cookie
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            
            account = Account.objects.create(
                user=user,
                account_number=Account.generate_account_number(),
                email_verification_token=default_token_generator.make_token(user)
            )
            
            verification_link = request.build_absolute_uri(
                reverse('verify_email', kwargs={
                    'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account.email_verification_token
                })
            )
            
            send_mail(
                'Verify your email for SecureBank',
                f'Please click the following link to verify your email: {verification_link}',
                'noreply@securebank.com',
                [user.email],
                fail_silently=False,
            )
            
            messages.success(request, 'Please check your email to verify your account.')
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = CustomUserCreationForm()
    return render(request, 'banking/register.html', {'form': form})


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        account = Account.objects.get(user=user)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, Account.DoesNotExist):
        user = None
        account = None

    if user is not None and account is not None and account.email_verification_token == token:
        user.is_active = True
        user.save()
        account.is_email_verified = True
        account.email_verification_token = None
        account.save()
        messages.success(request, 'Your email has been verified. You can now log in.')
        return redirect('login')
    else:
        messages.error(request, 'The verification link is invalid or has expired.')
        return redirect('home')

@ensure_csrf_cookie
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Generate and send 2FA code
            two_factor_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            request.session['two_factor_code'] = two_factor_code
            request.session['user_id'] = user.id
            request.session.save()
            
            send_mail(
                'Your login verification code',
                f'Your verification code is: {two_factor_code}',
                'noreply@securebank.com',
                [user.email],
                fail_silently=False,
            )
            
            return redirect('verify_login')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'banking/login.html')

@ensure_csrf_cookie
def verify_login(request):
    if request.method == 'POST':
        entered_code = request.POST.get('verification_code')
        stored_code = request.session.get('two_factor_code')
        user_id = request.session.get('user_id')

        if not stored_code or not user_id:
            messages.error(request, 'Verification session has expired. Please log in again.')
            return redirect('login')

        if entered_code == stored_code:
            try:
                user = User.objects.get(id=user_id)
                login(request, user)
                messages.success(request, 'Login successful!')
                
                # Clean up session data
                request.session.pop('two_factor_code', None)
                request.session.pop('user_id', None)
                
                return redirect('dashboard')
            except ObjectDoesNotExist:
                messages.error(request, 'User not found. Please try logging in again.')
                return redirect('login')
        else:
            messages.error(request, 'Invalid verification code. Please try again.')

    return render(request, 'banking/verify_login.html')

@login_required
def dashboard(request):
    user_account = request.user.account
    
    # Get recent transactions
    transactions = Transaction.objects.filter(account=user_account).order_by('-timestamp')[:5]
    
    # Get upcoming bills
    upcoming_bills = Bill.objects.filter(account=user_account, due_date__gte=timezone.now(), is_paid=False).order_by('due_date')[:5]
    
    # Calculate monthly spending (example data - replace with actual calculations)
    monthly_spending = [
        Transaction.objects.filter(account=user_account, timestamp__month=i, transaction_type='WITHDRAWAL').aggregate(total=Sum('amount'))['total'] or 0
        for i in range(1, 7)
    ]

    context = {
        'account': user_account,
        'transactions': transactions,
        'upcoming_bills': upcoming_bills,
        'monthly_spending': monthly_spending,
    }
    return render(request, 'banking/dashboard.html', context)

@login_required
def deposit(request):
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            to_account_number = form.cleaned_data['to_account_number']
            
            to_account = get_object_or_404(Account, account_number=to_account_number)
            
            account = request.user.account
            
            if BlockedTransaction.objects.filter(account=account, transaction_type='DEPOSIT').exists():
               messages.error(request, 'Deposits are currently blocked for your account.')
               return redirect('deposit')
            
            Transaction.objects.create(
            account=account,
            transaction_type='DEPOSIT',
            amount=amount,
            description=description,
            status='PENDING'
            )
            
            with db_transaction.atomic():
                Transaction.objects.create(
                    account=to_account,
                    transaction_type='DEPOSIT',
                    amount=amount,
                    description=description
                )
                to_account.balance += amount
                to_account.save()
            
            messages.success(request, f'Successfully deposited ${amount} to account {to_account_number}.')
            return redirect('dashboard')
    else:
        form = DepositForm()
    
    return render(request, 'banking/deposit.html', {'form': form})

@login_required
@ensure_csrf_cookie
def transfer(request):
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            from_account_number = form.cleaned_data['from_account_number']
            to_account_number = form.cleaned_data['to_account_number']
            
            from_account = get_object_or_404(Account, account_number=from_account_number)
            to_account = get_object_or_404(Account, account_number=to_account_number)
            
            if from_account.balance < amount:
                messages.error(request, 'Insufficient funds for transfer.')
                return redirect('transfer')
            
            if BlockedTransaction.objects.filter(account=from_account, transaction_type='TRANSFER').exists():
               messages.error(request, 'Transfers are currently blocked for your account.')
               return redirect('transfer')  
            
            transaction = Transaction.objects.create(
            account=from_account,
            transaction_type='TRANSFER',
            amount=amount,
            description=description,
            to_account=to_account,
            status='PENDING'
            )  
            
            with db_transaction.atomic():
                Transaction.objects.create(
                    account=from_account,
                    transaction_type='TRANSFER',
                    amount=amount,
                    description=description,
                    to_account=to_account
                )
                from_account.balance -= amount
                from_account.save()
                
                Transaction.objects.create(
                    account=to_account,
                    transaction_type='DEPOSIT',
                    amount=amount,
                    description=f'Transfer from {from_account_number}'
                )
                to_account.balance += amount
                to_account.save()
            
            messages.success(request, f'Successfully transferred ${amount} from account {from_account_number} to account {to_account_number}.')
            return redirect('dashboard')
    else:
        form = TransferForm()
    
    return render(request, 'banking/transfer.html', {'form': form})

@login_required
def withdrawal(request):
    if request.method == 'POST':
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            from_account_number = form.cleaned_data['from_account_number']
            
            from_account = get_object_or_404(Account, account_number=from_account_number)
            
            account = request.user.account
            
            if from_account.balance < amount:
                messages.error(request, 'Insufficient funds for withdrawal.')
                return redirect('withdrawal')
            
            if BlockedTransaction.objects.filter(account=account, transaction_type='WITHDRAWAL').exists():
               messages.error(request, 'Withdrawals are currently blocked for your account.')
               return redirect('withdrawal')
            
            Transaction.objects.create(
            account=account,
            transaction_type='WITHDRAWAL',
            amount=amount,
            description=description,
            status='PENDING'
            )
            
            with db_transaction.atomic():
                Transaction.objects.create(
                    account=from_account,
                    transaction_type='WITHDRAWAL',
                    amount=amount,
                    description=description
                )
                from_account.balance -= amount
                from_account.save()
            
            messages.success(request, f'Successfully withdrew ${amount} from account {from_account_number}.')
            return redirect('dashboard')
    else:
        form = WithdrawalForm()
    
    return render(request, 'banking/withdrawal.html', {'form': form})

@login_required
def transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.account = request.user.account
            
            if transaction.transaction_type == 'WITHDRAWAL' and transaction.amount > request.user.account.balance:
                messages.error(request, 'Insufficient funds.')
            else:
                transaction.save()
                
                if transaction.transaction_type == 'DEPOSIT':
                    request.user.account.balance += transaction.amount
                elif transaction.transaction_type == 'WITHDRAWAL':
                    request.user.account.balance -= transaction.amount
                
                request.user.account.save()
                messages.success(request, 'Transaction completed successfully.')
                return redirect('dashboard')
    else:
        form = TransactionForm()
    return render(request, 'banking/transaction.html', {'form': form})

@login_required
def setup_2fa(request):
    if request.method == 'POST':
        device = TOTPDevice.objects.create(user=request.user, name='Default')
        return render(request, 'banking/setup_2fa.html', {'device': device})
    return render(request, 'banking/setup_2fa.html')

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        account = self.get_object()
        amount = request.data.get('amount')
        to_account_number = request.data.get('to_account')

        try:
            to_account = Account.objects.get(account_number=to_account_number)
        except Account.DoesNotExist:
            return Response({'error': 'Recipient account not found.'}, status=400)

        if account.balance < float(amount):
            return Response({'error': 'Insufficient funds.'}, status=400)

        account.balance -= float(amount)
        to_account.balance += float(amount)
        account.save()
        to_account.save()

        Transaction.objects.create(account=account, transaction_type='TRANSFER', amount=amount, description=f'Transfer to {to_account_number}')
        Transaction.objects.create(account=to_account, transaction_type='DEPOSIT', amount=amount, description=f'Transfer from {account.account_number}')

        return Response({'message': 'Transfer successful.'})

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(account__user=self.request.user)

@login_required
def pay_bill(request):
    if request.method == 'POST':
        bill_id = request.POST.get('bill_id')
        try:
            bill = Bill.objects.get(id=bill_id, account=request.user.account, is_paid=False)
            if request.user.account.balance >= bill.amount:
                # Create a transaction for bill payment
                Transaction.objects.create(
                    account=request.user.account,
                    transaction_type='WITHDRAWAL',
                    amount=bill.amount,
                    description=f"Payment for {bill.name}"
                )
                
                # Update account balance
                request.user.account.balance -= bill.amount
                request.user.account.save()
                
                # Mark bill as paid
                bill.is_paid = True
                bill.save()
                
                messages.success(request, f"Successfully paid {bill.name} for ${bill.amount}")
            else:
                messages.error(request, "Insufficient funds to pay this bill")
        except Bill.DoesNotExist:
            messages.error(request, "Invalid bill selection")
        return redirect('dashboard')
    
    # If it's a GET request, display unpaid bills
    unpaid_bills = Bill.objects.filter(account=request.user.account, is_paid=False).order_by('due_date')
    return render(request, 'banking/pay_bill.html', {'unpaid_bills': unpaid_bills})
@require_http_methods(["GET", "POST"])
def custom_logout(request):
    logout(request)
    return redirect('home')

@login_required
def notifications(request):
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all unread notifications as read
    unread_notifications = user_notifications.filter(is_read=False)
    unread_notifications.update(is_read=True)
    
    context = {
        'notifications': user_notifications,
    }
    return render(request, 'banking/notification.html', context)

@ensure_csrf_cookie
def set_csrf_cookie(request):
    return JsonResponse({'success': True})

@login_required
def chat_room(request, room_name):
    return render(request, 'banking/chat_room.html', {
        'room_name': room_name
    })
    
def is_staff(user):
    return user.is_staff

@login_required
@user_passes_test(is_staff)
def agent_interface(request):
    return render(request, 'banking/agent_interface.html')    