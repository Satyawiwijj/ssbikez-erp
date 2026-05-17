from django.urls import path

from . import views

app_name = 'spares'

urlpatterns = [
    # SparesCategory
    path('categories/',                          views.category_list,             name='category_list'),
    path('categories/create/',                   views.category_create,           name='category_create'),
    path('categories/<int:pk>/edit/',            views.category_update,           name='category_update'),

    # SparePart
    path('parts/',                               views.part_list,                 name='part_list'),
    path('parts/create/',                        views.part_create,               name='part_create'),
    path('parts/<int:pk>/',                      views.part_detail,               name='part_detail'),
    path('parts/<int:pk>/edit/',                 views.part_update,               name='part_update'),

    # Supplier
    path('suppliers/',                           views.supplier_list,             name='supplier_list'),
    path('suppliers/create/',                    views.supplier_create,           name='supplier_create'),
    path('suppliers/<int:pk>/',                  views.supplier_detail,           name='supplier_detail'),
    path('suppliers/<int:pk>/edit/',             views.supplier_update,           name='supplier_update'),

    # PurchaseOrder
    path('purchase-orders/',                     views.po_list,                   name='po_list'),
    path('purchase-orders/create/',              views.po_create,                 name='po_create'),
    path('purchase-orders/<int:pk>/',            views.po_detail,                 name='po_detail'),
    path('purchase-orders/<int:pk>/edit/',       views.po_update,                 name='po_update'),
    path('purchase-orders/<int:pk>/status/',     views.po_status_update,          name='po_status_update'),

    # PurchaseOrderItem
    path('po-items/create/',                     views.po_item_create,            name='po_item_create'),
    path('po-items/<int:pk>/edit/',              views.po_item_update,            name='po_item_update'),
    path('po-items/<int:pk>/delete/',            views.po_item_delete,            name='po_item_delete'),

    # CounterSale
    path('counter-sales/',                       views.counter_sale_list,         name='counter_sale_list'),
    path('counter-sales/create/',                views.counter_sale_create,       name='counter_sale_create'),
    path('counter-sales/<int:pk>/',              views.counter_sale_detail,       name='counter_sale_detail'),
    path('counter-sales/<int:pk>/edit/',         views.counter_sale_update,       name='counter_sale_update'),

    # CounterSaleItem
    path('counter-sale-items/create/',           views.counter_sale_item_create,  name='counter_sale_item_create'),
    path('counter-sale-items/<int:pk>/delete/',  views.counter_sale_item_delete,  name='counter_sale_item_delete'),

    # SparesIssue
    path('issues/',                              views.issue_list,                name='issue_list'),
    path('issues/create/',                       views.issue_create,              name='issue_create'),
    path('issues/<int:pk>/edit/',                views.issue_update,              name='issue_update'),
]
