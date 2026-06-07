from django.db import models
from apps.core.models import Party
from apps.labor.models import Labor
from django.db.models import Sum

class Sample(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='samples')
    labor = models.ForeignKey(Labor, on_delete=models.CASCADE, related_name='sample_work')
    sample_name = models.CharField(max_length=200, verbose_name="Sample Name/Code")
    total_pieces = models.PositiveIntegerField(default=0)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    work_date = models.DateField()
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.total_amount = (self.total_pieces or 0) * self.rate
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-work_date', '-created_at']
        indexes = [
            models.Index(fields=['work_date']),
            models.Index(fields=['party']),
            models.Index(fields=['labor']),
        ]

    def __str__(self):
        return f"{self.sample_name} - {self.party.name}"

