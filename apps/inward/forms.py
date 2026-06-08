from django import forms
from .models import Inward


class InwardForm(forms.ModelForm):
    class Meta:
        model = Inward
        fields = [
            "sr_no",
            "challan_no",
            "date",
            "delivery_party",
            "buyer_party",
            "article_no",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "sr_no": forms.NumberInput(attrs={"class": "form-input"}),
            "challan_no": forms.TextInput(attrs={"class": "form-input"}),
            "delivery_party": forms.TextInput(attrs={"class": "form-input"}),
            "buyer_party": forms.TextInput(attrs={"class": "form-input"}),
            "article_no": forms.TextInput(attrs={"class": "form-input"}),
        }

    def clean_sr_no(self):
        sr_no = self.cleaned_data.get("sr_no")
        if Inward.objects.filter(sr_no=sr_no).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Serial Number already exists.")
        return sr_no
