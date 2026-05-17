from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',              views.login_view,   name='login'),
    path('logout/',             views.logout_view,  name='logout'),
    path('dashboard/',          views.dashboard,    name='dashboard'),

    path('users/',              views.user_list,    name='user_list'),
    path('users/create/',       views.user_create,  name='user_create'),
    path('users/<int:pk>/edit/', views.user_update, name='user_update'),

    path('branches/',           views.branch_list,  name='branch_list'),
    path('branches/create/',    views.branch_create, name='branch_create'),

    path('roles/',              views.role_list,    name='role_list'),
]
