from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from banking import views
from rest_framework.routers import DefaultRouter
from django.contrib.auth.views import LogoutView

router = DefaultRouter()
router.register(r'accounts', views.AccountViewSet)
router.register(r'transactions', views.TransactionViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('deposit/', views.deposit, name='deposit'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('pay-bill/', views.pay_bill, name='pay_bill'),
    path('transfer/', views.transfer, name='transfer'),
    path('withdrawal/', views.withdrawal, name='withdrawal'),
    path('transaction/', views.transaction, name='transaction'),
    path('verify-login/', views.verify_login, name='verify_login'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='banking/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='banking/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='banking/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='banking/password_reset_complete.html'), name='password_reset_complete'),
    path('setup-2fa/', views.setup_2fa, name='setup_2fa'),
    path('captcha/', include('captcha.urls')),
    path('api/', include(router.urls)),
    path('notifications/', views.notifications, name='notifications'),
    path('set-csrf-cookie/', views.set_csrf_cookie, name='set_csrf_cookie'),
    path('chat/<str:room_name>/', views.chat_room, name='chat_room'),
    path('agent/', views.agent_interface, name='agent_interface'),
]