from django.db import models

class Operation(models.Model):
    name = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)
    has_sub_operations = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.name

class SubOperation(models.Model):
    operation = models.ForeignKey(Operation, on_delete=models.CASCADE, related_name='sub_operations')
    name = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"{self.operation.name} - {self.name}"
