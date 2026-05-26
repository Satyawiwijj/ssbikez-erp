from django.contrib import admin
from .models import (
    SparesItem, ItemRackBin, StockLedger,
    SupplierQuote, SupplierQuoteItem,
    PurchaseOrder, PurchaseOrderItem,
    PurchaseInvoice, PurchaseInvoiceItem,
    CounterSale, CounterSaleItem,
    CounterSaleReturn, CounterSaleReturnItem,
    SparesIssueAlteration, SparesIssueAlterationItem,
)


class SupplierQuoteItemInline(admin.TabularInline):
    model = SupplierQuoteItem
    extra = 1


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


class PurchaseInvoiceItemInline(admin.TabularInline):
    model = PurchaseInvoiceItem
    extra = 1


class CounterSaleItemInline(admin.TabularInline):
    model = CounterSaleItem
    extra = 1


class CounterSaleReturnItemInline(admin.TabularInline):
    model = CounterSaleReturnItem
    extra = 1


class SparesIssueAlterationItemInline(admin.TabularInline):
    model = SparesIssueAlterationItem
    extra = 1


@admin.register(SparesItem)
class SparesItemAdmin(admin.ModelAdmin):
    list_display = ['item_code', 'item_name', 'category', 'uom', 'mrp', 'is_active']
    list_filter = ['category', 'is_active', 'brand']
    search_fields = ['item_code', 'item_name', 'part_number', 'hsn_sac']


@admin.register(ItemRackBin)
class ItemRackBinAdmin(admin.ModelAdmin):
    list_display = ['item', 'rack', 'bin', 'is_active']


@admin.register(StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    list_display = ['item', 'warehouse', 'rack', 'bin', 'quantity', 'updated_at']
    list_filter = ['warehouse']


@admin.register(SupplierQuote)
class SupplierQuoteAdmin(admin.ModelAdmin):
    list_display = ['quote_no', 'supplier', 'date', 'status', 'grand_total']
    list_filter = ['status']
    inlines = [SupplierQuoteItemInline]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_no', 'supplier', 'date', 'status', 'grand_total']
    list_filter = ['status']
    inlines = [PurchaseOrderItemInline]


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_no', 'supplier', 'date', 'status', 'grand_total', 'payment_status']
    list_filter = ['status', 'payment_status']
    inlines = [PurchaseInvoiceItemInline]


@admin.register(CounterSale)
class CounterSaleAdmin(admin.ModelAdmin):
    list_display = ['sale_no', 'customer', 'mobile', 'date', 'status', 'total_amount']
    list_filter = ['status', 'payment_status']
    inlines = [CounterSaleItemInline]


@admin.register(CounterSaleReturn)
class CounterSaleReturnAdmin(admin.ModelAdmin):
    list_display = ['return_no', 'original_sale', 'return_date', 'total_amount']
    inlines = [CounterSaleReturnItemInline]


@admin.register(SparesIssueAlteration)
class SparesIssueAlterationAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'job_card', 'date', 'job_type', 'total']
    list_filter = ['job_type']
    inlines = [SparesIssueAlterationItemInline]
