from django.contrib import admin
from .models import Sample

@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ('sample_name', 'party', 'labor', 'total_pieces', 'total_amount', 'work_date')
    list_filter = ('work_date', 'party', 'labor')
    search_fields = ('sample_name', 'party__name', 'labor__name')
    date_hierarchy = 'work_date'
