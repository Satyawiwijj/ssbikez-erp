from django.urls import path

from . import views

app_name = 'customers'

urlpatterns = [
    # Customer
    path('',                         views.customer_list,         name='customer_list'),
    path('customers/',               views.customer_list),         # alias
    path('<int:pk>/',                views.customer_detail,       name='customer_detail'),
    path('customers/<int:pk>/',      views.customer_detail),       # alias
    path('create/',                  views.customer_create,       name='customer_create'),
    path('customers/create/',        views.customer_create),       # alias
    path('<int:pk>/edit/',           views.customer_update,       name='customer_update'),
    path('<int:pk>/delete/',         views.customer_delete,       name='customer_delete'),

    # BikeModel
    path('bikes/',                   views.bike_model_list,       name='bike_model_list'),
    path('bike-models/',             views.bike_model_list),       # alias
    path('bikes/<int:pk>/',          views.bike_model_detail,     name='bike_model_detail'),
    path('bike-models/<int:pk>/',    views.bike_model_detail),     # alias
    path('bikes/create/',            views.bike_model_create,     name='bike_model_create'),
    path('bike-models/create/',      views.bike_model_create),     # alias
    path('bikes/<int:pk>/edit/',     views.bike_model_update,     name='bike_model_update'),

    # VehicleStock
    path('stock/',                   views.vehicle_stock_list,    name='vehicle_stock_list'),
    path('vehicle-stock/',           views.vehicle_stock_list),    # alias
    path('vehicle-stock/aging/',     views.stock_aging,           name='stock_aging'),
    path('stock/<int:pk>/',          views.vehicle_stock_detail,  name='vehicle_stock_detail'),
    path('vehicle-stock/<int:pk>/',  views.vehicle_stock_detail),  # alias
    path('stock/create/',            views.vehicle_stock_create,  name='vehicle_stock_create'),
    path('vehicle-stock/create/',    views.vehicle_stock_create),  # alias
    path('stock/<int:pk>/edit/',     views.vehicle_stock_update,  name='vehicle_stock_update'),
]
