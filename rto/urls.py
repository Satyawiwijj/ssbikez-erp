from django.urls import path

from . import views

app_name = 'rto'

urlpatterns = [
    # RTORegistration
    path('',                              views.registration_list,          name='registration_list'),
    path('create/',                       views.registration_create,        name='registration_create'),
    path('<int:pk>/',                     views.registration_detail,        name='registration_detail'),
    path('<int:pk>/edit/',                views.registration_update,        name='registration_update'),
    path('<int:pk>/status/',              views.registration_status_update, name='registration_status_update'),

    # NumberPlateOrder
    path('plates/create/',                views.plate_create,               name='plate_create'),
    path('plates/<int:pk>/edit/',         views.plate_update,               name='plate_update'),
]
