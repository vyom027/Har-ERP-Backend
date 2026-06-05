from django.db import models
from django.db.models import Sum

class Labor(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    joining_date = models.DateField(auto_now_add=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @property
    def total_earned(self):
        from apps.production.models import WorkEntry
        from apps.samples.models import Sample
        production_earned = WorkEntry.objects.filter(labor=self).aggregate(total=Sum('total_amount'))['total'] or 0
        samples_earned = Sample.objects.filter(labor=self).aggregate(total=Sum('total_amount'))['total'] or 0
        return production_earned + samples_earned

    @property
    def total_paid(self):
        return self.payments.aggregate(total=Sum('amount'))['total'] or 0

    @property
    def pending_balance(self):
        return self.total_earned - self.total_paid

class Payment(models.Model):
    PAYMENT_TYPES = [
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('other', 'Other'),
    ]
    labor = models.ForeignKey(Labor, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='cash')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.labor.name} - {self.amount} ({self.payment_date})"
