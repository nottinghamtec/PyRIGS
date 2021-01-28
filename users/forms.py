from captcha.fields import ReCaptchaField
from django import forms
from django.contrib.auth.forms import (AuthenticationForm, PasswordResetForm,
                                       UserChangeForm, UserCreationForm)
from registration.forms import RegistrationFormUniqueEmail

from RIGS import models


# Registration
class ProfileRegistrationFormUniqueEmail(RegistrationFormUniqueEmail):
    captcha = ReCaptchaField()

    class Meta:
        model = models.Profile
        fields = ('username', 'email', 'first_name', 'last_name', 'initials')

    def clean_initials(self):
        """
        Validate that the supplied initials are unique.
        """
        if models.Profile.objects.filter(initials__iexact=self.cleaned_data['initials']):
            raise forms.ValidationError("These initials are already in use. Please supply different initials.")
        return self.cleaned_data['initials']


class CheckApprovedForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if user.is_approved or user.is_superuser:
            return AuthenticationForm.confirm_login_allowed(self, user)
        else:
            raise forms.ValidationError(
                "Your account hasn't been approved by an administrator yet. Please check back in a few minutes!")


# Embedded Login form - remove the autofocus
class EmbeddedAuthenticationForm(CheckApprovedForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.pop('autofocus', None)


class PasswordReset(PasswordResetForm):
    captcha = ReCaptchaField(label='Captcha')


class ProfileCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = models.Profile


class ProfileChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = models.Profile
