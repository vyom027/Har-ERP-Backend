from django.db import models

class Party(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Lot(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('shipped', 'Shipped'),
    ]
    lot_number = models.CharField(max_length=50, unique=True)
    party = models.ForeignKey(Party, on_delete=models.CASCADE)
    total_pieces = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.lot_number

class LotColor(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name='colors')
    color_name = models.CharField(max_length=50)
    pieces = models.PositiveIntegerField()
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.lot.lot_number} - {self.color_name}"
