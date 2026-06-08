from django.contrib import admin
from .models import Inward, InwardItem

class InwardItemInline(admin.TabularInline):
    model = InwardItem
    extra = 1

@admin.register(Inward)
class InwardAdmin(admin.ModelAdmin):
    list_display = (
        "sr_no",
        "challan_no",
        "date",
        "delivery_party",
        "buyer_party",
        "article_no",
    )
    search_fields = ("challan_no", "delivery_party", "buyer_party", "article_no")
    list_filter = ("date",)
    inlines = [InwardItemInline]
