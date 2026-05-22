from django.db import models
from django.conf import settings


class SparesCategory(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Spares Categories'
        ordering = ['name']


class Supplier(models.Model):
    supplier_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    gstin = models.CharField(max_length=20, blank=True)
    gst_category = models.CharField(max_length=50, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    place_of_supply = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.supplier_name

    class Meta:
        ordering = ['supplier_name']


class Warehouse(models.Model):
    WAREHOUSE_TYPES = [
        ('transit', 'Goods In Transit'),
        ('finished', 'Finished Goods'),
        ('wip', 'Work In Progress'),
        ('stores', 'Stores'),
        ('all', 'All Warehouses'),
        ('rejected', 'Rejected'),
    ]
    name = models.CharField(max_length=200)
    warehouse_type = models.CharField(max_length=20, choices=WAREHOUSE_TYPES, blank=True)
    is_group = models.BooleanField(default=False)
    parent_warehouse = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children'
    )
    is_rejected = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pin = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Rack(models.Model):
    name = models.CharField(max_length=100)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='racks')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.warehouse.name} / {self.name}"

    class Meta:
        ordering = ['warehouse', 'name']


class Bin(models.Model):
    name = models.CharField(max_length=100)
    rack = models.ForeignKey(Rack, on_delete=models.CASCADE, related_name='bins')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rack} / {self.name}"

    class Meta:
        ordering = ['rack', 'name']
