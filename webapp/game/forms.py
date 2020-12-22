from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from game.models import Profile

MAX_UPLOAD_SIZE = 25000000


class ProfileForm(forms.ModelForm):
    bio = forms.CharField(required=False)

    class Meta:
        model = Profile
        fields = ['picture', 'bio']

    def clean_picture(self):
        picture = self.cleaned_data.get('picture')
        if picture is None:
            return picture

        if not picture.content_type or not picture.content_type.startswith('image'):
            raise forms.ValidationError('You must upload a picture')
        if picture.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError('This picture is too big')
        return picture


class LoginForm(forms.Form):
    username = forms.CharField(max_length=20)
    password = forms.CharField(max_length=20, widget=forms.PasswordInput())

    # customize validation methods to verify login info
    def clean(self):
        # call super class clean() to fetch data
        clean_data = super().clean()

        # verify user credentials
        username = clean_data.get('username')
        password = clean_data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            raise forms.ValidationError('Incorrect username/password')

        # return clean data
        return clean_data


class RegisterForm(forms.Form):
    username = forms.CharField(max_length=20)
    password = forms.CharField(max_length=20, widget=forms.PasswordInput())
    confirm_password = forms.CharField(max_length=20, widget=forms.PasswordInput())
    email = forms.CharField(max_length=30, widget=forms.EmailInput())
    first_name = forms.CharField(max_length=20)
    last_name = forms.CharField(max_length=20)
    GENDER = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female')
    ]
    gender = forms.ChoiceField(choices=GENDER, widget=forms.RadioSelect)

    # verify password consistency
    def clean(self):
        clean_data = super().clean()

        password = clean_data.get('password')
        confirm_password = clean_data.get('confirm_password')
        if password != confirm_password:
            raise forms.ValidationError('Passwords don\'t match')

        return clean_data

    # check username not been used
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__exact=username):
            raise forms.ValidationError('User name been used')

        return username

