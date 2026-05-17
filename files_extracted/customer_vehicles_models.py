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
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Customer Vehicles'

    def __str__(self):
        reg = self.registration_no or 'Unregistered'
        return f"{self.customer} — {self.vehicle.bike_model} ({reg})"
