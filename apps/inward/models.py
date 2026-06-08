from django.db import models

class Inward(models.Model):
    sr_no = models.IntegerField(unique=True, verbose_name="Sr No")
    challan_no = models.CharField(max_length=100, verbose_name="Challan No")
    date = models.DateField(verbose_name="Date")
    delivery_party = models.CharField(max_length=255, verbose_name="Delivery Party")
    buyer_party = models.CharField(max_length=255, verbose_name="Buyer Party")
    article_no = models.CharField(max_length=100, verbose_name="Article No")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inward {self.sr_no} - {self.challan_no}"

    class Meta:
        ordering = ["-sr_no"]

class InwardItem(models.Model):
    inward = models.ForeignKey(Inward, on_delete=models.CASCADE, related_name='items')
    roll_no = models.CharField(max_length=100, verbose_name="Roll No")
    color = models.CharField(max_length=100, verbose_name="Color", blank=True)
    meters = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Meters")

    def __str__(self):
        return f"{self.inward.challan_no} - {self.roll_no}"
