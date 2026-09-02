from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Profile  # 👈 Yeh import missing tha, ab add ho gaya!

class SignUpForm(UserCreationForm):
    full_name = forms.CharField(
        max_length=100, 
        required=True, 
        label="Full Name",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Mashood Arshad',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-emerald focus:border-transparent text-sm transition'
        })
    )
    email = forms.EmailField(
        required=True, 
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'placeholder': 'name@example.com',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-emerald focus:border-transparent text-sm transition'
        })
    )
    phone = forms.CharField(
        max_length=15, 
        required=True, 
        label="Phone Number (for COD Delivery)",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., 03297185977',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-emerald focus:border-transparent text-sm transition'
        })
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            if field_name not in ['full_name', 'email', 'phone']:
                self.fields[field_name].widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-emerald focus:border-transparent text-sm transition'
                })

    def save(self, commit=True):
        user = super().save(commit=False)
        names = self.cleaned_data['full_name'].split(' ', 1)
        user.first_name = names[0]
        if len(names) > 1:
            user.last_name = names[1]
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # Ab Python ko pata hai ke Profile kya hai!
            profile, created = Profile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data['phone']
            profile.save()
        return user