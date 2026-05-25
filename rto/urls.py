from django.urls import path

from . import views

app_name = 'rto'

urlpatterns = [
    # Dashboard
    path('dashboard/',                    views.dashboard,                  name='dashboard'),

    # NumberPlate list
    path('plates/',                       views.plate_list,                 name='plate_list'),

    # RTORegistration
    path('',                              views.registration_list,          name='registration_list'),
    path('create/',                       views.registration_create,        name='registration_create'),
    path('<int:pk>/',                     views.registration_detail,        name='registration_detail'),
    path('<int:pk>/edit/',                views.registration_update,        name='registration_update'),
    path('<int:pk>/status/',              views.registration_status_update, name='registration_status_update'),

    # NumberPlateOrder
    path('plates/create/',                views.plate_create,               name='plate_create'),
    path('plates/<int:pk>/edit/',         views.plate_update,               name='plate_update'),

    # RC Book
    path('rc-books/',                     views.rc_book_list,               name='rc_book_list'),
    path('rc-books/<int:pk>/',            views.rc_book_detail,             name='rc_book_detail'),
    path('<int:rto_pk>/rc-book/',         views.rc_book_create,             name='rc_book_create'),
]
