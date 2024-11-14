from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class StockFilterForm(forms.Form):
    new_bra = forms.BooleanField(label='new_bra', required=False)
    w3 = forms.BooleanField(label='w3', required=False)
    consen = forms.BooleanField(label='consen', required=False)
    sun = forms.BooleanField(label='sun', required=False)