from django import forms
from .models import Order

PRODUCT_QUANTITY_CHOICES = [(i, str(i)) for i in range(1, 21)]

class CartAddProductForm(forms.Form):
    quantity = forms.TypedChoiceField(choices=PRODUCT_QUANTITY_CHOICES, coerce=int, label="Quantité")
    override = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Prénom', 'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Nom', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Téléphone', 'class': 'form-input'}),
            'address': forms.TextInput(attrs={'placeholder': 'Adresse', 'class': 'form-input'}),
            'city': forms.TextInput(attrs={'placeholder': 'Ville', 'class': 'form-input'}),
        }
