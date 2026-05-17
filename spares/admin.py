from django.contrib import admin

from .models import (CounterSale, CounterSaleItem, PurchaseOrder,
                     PurchaseOrderItem, SparePart, SparesCategory,
                     SparesIssue, Supplier)


@admin.register(SparesCategory)
class SparesCategoryAdmin(admin.ModelAdmin):
    list_display    = ('category_name', 'created_at')
    search_fields   = ('category_name',)
    readonly_fields = ('created_at',)


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display    = ('part_name', 'part_number', 'category', 'mrp',
                       'stock_quantity', 'rack_location', 'bin_location')
    search_fields   = ('part_name', 'part_number')
    list_filter     = ('category',)
    readonly_fields = ('created_at',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display    = ('supplier_name', 'phone', 'email')
    search_fields   = ('supplier_name', 'phone', 'email')
    readonly_fields = ('created_at',)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display    = ('supplier', 'order_date', 'total_amount', 'status')
    list_filter     = ('status',)
    readonly_fields = ('order_date', 'created_at')


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display    = ('purchase_order', 'spare_part', 'quantity', 'price')
    readonly_fields = ('created_at',)


@admin.register(CounterSale)
class CounterSaleAdmin(admin.ModelAdmin):
    list_display    = ('invoice_number', 'customer', 'total_amount',
                       'sale_date', 'created_by')
    search_fields   = ('invoice_number', 'customer__full_name', 'customer__phone')
    list_filter     = ('sale_date',)
    readonly_fields = ('sale_date', 'created_at')


@admin.register(CounterSaleItem)
class CounterSaleItemAdmin(admin.ModelAdmin):
    list_display = ('counter_sale', 'spare_part', 'quantity',
                    'unit_price', 'total_price')


@admin.register(SparesIssue)
class SparesIssueAdmin(admin.ModelAdmin):
    list_display    = ('job_card', 'spare_part', 'quantity_issued',
                       'quantity_returned', 'issued_by', 'issued_at')
    search_fields   = ('job_card__id', 'spare_part__part_name')
    list_filter     = ('issued_at',)
    readonly_fields = ('issued_at',)
