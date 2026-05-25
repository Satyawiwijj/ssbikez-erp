from django.db import models


class CustomerVehicle(models.Model):
    """
    Bridge table — created by Team 1 (sales) after a sale closes.
    Read by Team 2 (service, spares, vas) for all workshop operations.
    """
    customer         = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    vehicle          = models.ForeignKey(
        'customers.VehicleStock',
        on_delete=models.PROTECT,
        related_name='customer_vehicles'
    )
    registration_no  = models.CharField(max_length=50, blank=True, null=True)
    purchase_date    = models.DateField(blank=True, null=True)
    insurance_expiry = models.DateField(blank=True, null=True)

    # GAP 31 — Warranty status tracking
    warranty_start_date = models.DateField(null=True, blank=True)
    warranty_end_date   = models.DateField(null=True, blank=True)
    total_free_services = models.IntegerField(default=5)
    free_services_used  = models.IntegerField(default=0)

    created_at       = models.DateTimeField(auto_now_add=True)

    @property
    def warranty_active(self):
        from datetime import date
        if self.warranty_end_date:
            return self.warranty_end_date >= date.today()
        return False

    @property
    def free_services_remaining(self):
        return max(0, self.total_free_services - self.free_services_used)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Customer Vehicles'

    def __str__(self):
        reg = self.registration_no or 'Unregistered'
        return f"{self.customer} — {self.vehicle.bike_model} ({reg})"
