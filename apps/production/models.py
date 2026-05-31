from django.db import models
from apps.core.models import Lot, LotColor
from apps.labor.models import Labor
from apps.operations.models import Operation, SubOperation

class WorkEntry(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE)
    lot_color = models.ForeignKey(LotColor, on_delete=models.CASCADE, null=True, blank=True)
    labor = models.ForeignKey(Labor, on_delete=models.CASCADE)
    operation = models.ForeignKey(Operation, on_delete=models.CASCADE)
    sub_operation = models.ForeignKey(SubOperation, on_delete=models.CASCADE, null=True, blank=True)
    size = models.CharField(max_length=20, blank=True, null=True)
    pieces = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    work_date = models.DateField()
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.total_amount = self.pieces * self.rate
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['work_date']),
            models.Index(fields=['labor']),
            models.Index(fields=['lot']),
            models.Index(fields=['operation']),
        ]

    def __str__(self):
        return f"{self.lot.lot_number} - {self.operation.name} - {self.labor.name}"
