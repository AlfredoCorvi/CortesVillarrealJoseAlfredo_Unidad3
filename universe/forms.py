from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label='Correo electrónico',
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['autocomplete'] = 'username'


class LoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'No se pudo iniciar sesión. Revisa tu usuario y contraseña.',
        'inactive': 'No se pudo iniciar sesión. Revisa tu usuario y contraseña.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'autocomplete': 'username',
            'autocapitalize': 'none',
            'spellcheck': 'false',
        })
        self.fields['password'].widget.attrs['autocomplete'] = 'current-password'
