from django.urls import path

from . import views

app_name = 'customers'

urlpatterns = [
    # Customer
    path('',                         views.customer_list,         name='customer_list'),
    path('<int:pk>/',                views.customer_detail,       name='customer_detail'),
    path('create/',                  views.customer_create,       name='customer_create'),
    path('<int:pk>/edit/',           views.customer_update,       name='customer_update'),

    # BikeModel
    path('bikes/',                   views.bike_model_list,       name='bike_model_list'),
    path('bikes/<int:pk>/',          views.bike_model_detail,     name='bike_model_detail'),
    path('bikes/create/',            views.bike_model_create,     name='bike_model_create'),
    path('bikes/<int:pk>/edit/',     views.bike_model_update,     name='bike_model_update'),

    # VehicleStock
    path('stock/',                   views.vehicle_stock_list,    name='vehicle_stock_list'),
    path('stock/<int:pk>/',          views.vehicle_stock_detail,  name='vehicle_stock_detail'),
    path('stock/create/',            views.vehicle_stock_create,  name='vehicle_stock_create'),
    path('stock/<int:pk>/edit/',     views.vehicle_stock_update,  name='vehicle_stock_update'),
]
