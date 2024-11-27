from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        
    email = forms.EmailField(max_length=254, help_text='Required. Enter a valid email address.')
        
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')