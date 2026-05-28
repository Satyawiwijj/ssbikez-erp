from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',              views.login_view,   name='login'),
    path('logout/',             views.logout_view,  name='logout'),
    path('verify-otp/',         views.verify_otp,   name='verify_otp'),
    path('dashboard/',          views.dashboard,    name='dashboard'),

    path('users/',               views.user_list,    name='user_list'),
    path('users/create/',        views.user_create,  name='user_create'),
    path('users/<int:pk>/edit/', views.user_update,  name='user_update'),

    path('branches/',                    views.branch_list,   name='branch_list'),
    path('branches/create/',             views.branch_create, name='branch_create'),
    path('branches/<int:pk>/edit/',      views.branch_update, name='branch_update'),

    path('home/',                views.home,         name='home'),
    path('roles/',               views.role_list,   name='role_list'),
    path('roles/create/',        views.role_create, name='role_create'),
    path('roles/<int:pk>/edit/', views.role_update, name='role_update'),

    path('fuel-expenses/',               views.fuel_expense_list,   name='fuel_expense_list'),
    path('fuel-expenses/create/',        views.fuel_expense_create, name='fuel_expense_create'),
    path('fuel-expenses/<int:pk>/edit/', views.fuel_expense_update, name='fuel_expense_update'),

    # Profile
    path('profile/',      views.profile_view,   name='profile'),
    path('profile/edit/', views.profile_update, name='profile_update'),

    # Global search
    path('search/', views.global_search, name='search'),

    # Password change (requires login)
    path('password/change/', views.password_change, name='password_change'),

    # Password reset (no login required)
    path('password/reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url='/accounts/password/reset/done/',
    ), name='password_reset'),
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/password/reset/complete/',
    ), name='password_reset_confirm'),
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Reports
    path('reports/sales/',   views.sales_report,   name='sales_report'),
    path('reports/spares/',  views.spares_report,  name='spares_report'),
    path('reports/service/', views.service_report, name='service_report'),

    # Insurance Expiry
    path('insurance-expiry/', views.insurance_expiry_list, name='insurance_expiry_list'),

    # Company Settings
    path('settings/', views.company_settings, name='company_settings'),

    # Notifications
    path('notifications/',       views.notification_list,  name='notification_list'),
    path('notifications/count/', views.notification_count, name='notification_count'),
]
