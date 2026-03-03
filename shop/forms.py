from django import forms

from .models import Order


class CartAddProductForm(forms.Form):
    quantity = forms.IntegerField(
        label='Quantite',
        min_value=1,
        max_value=20,
        initial=1,
        widget=forms.NumberInput(
            attrs={
                'type': 'number',
                'min': '1',
                'max': '20',
                'step': '1',
                'class': 'qty-number-input',
            }
        ),
    )
    selected_color = forms.ChoiceField(
        choices=(),
        label='Couleur',
        widget=forms.Select(attrs={'class': 'variant-select'}),
    )
    selected_size = forms.ChoiceField(
        choices=(),
        label='Taille',
        widget=forms.Select(attrs={'class': 'variant-select'}),
    )
    override = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)

    def __init__(self, *args, product=None, variant_hidden=False, **kwargs):
        super().__init__(*args, **kwargs)

        color_choices = []
        size_choices = []
        if product is not None:
            color_choices = [(value, value) for value in product.get_color_options()]
            size_choices = [(value, value) for value in product.get_size_options()]

        if not color_choices:
            color_choices = [('Noir', 'Noir'), ('Vert', 'Vert')]
        if not size_choices:
            size_choices = [('M', 'M')]

        if product is not None:
            self.fields['selected_size'].label = product.size_label

        if variant_hidden:
            self.fields['selected_color'].choices = color_choices
            self.fields['selected_size'].choices = size_choices
            self.initial.setdefault('selected_color', color_choices[0][0])
            self.initial.setdefault('selected_size', size_choices[0][0])
        else:
            self.fields['selected_color'].choices = color_choices
            self.initial.setdefault('selected_color', color_choices[0][0])
            if product is not None and product.has_single_size:
                self.fields['selected_size'].choices = size_choices
                self.fields['selected_size'].widget = forms.HiddenInput()
                self.initial.setdefault('selected_size', size_choices[0][0])
            else:
                self.fields['selected_size'].choices = size_choices
                self.initial.setdefault('selected_size', size_choices[0][0])

        if variant_hidden:
            self.fields['selected_color'].widget = forms.HiddenInput()
            self.fields['selected_size'].widget = forms.HiddenInput()


class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Prenom', 'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Nom', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Telephone', 'class': 'form-input'}),
            'address': forms.TextInput(attrs={'placeholder': 'Adresse', 'class': 'form-input'}),
            'city': forms.TextInput(attrs={'placeholder': 'Ville', 'class': 'form-input'}),
        }
