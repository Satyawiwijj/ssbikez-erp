from django.urls import path

from . import views

app_name = 'customer_vehicles'

urlpatterns = [
    path('',                     views.customervehicle_list,   name='customervehicle_list'),
    path('<int:pk>/',            views.customervehicle_detail, name='customervehicle_detail'),
    path('create/',              views.customervehicle_create, name='customervehicle_create'),
    path('<int:pk>/edit/',       views.customervehicle_update, name='customervehicle_update'),
]
