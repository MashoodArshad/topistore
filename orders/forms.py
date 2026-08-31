import re
from django import forms


class OrderCreateForm(forms.Form):
    """
    Professional checkout form with server-side validation.
    Validates Pakistani phone numbers and required delivery fields.
    """
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Muhammad Ahmad',
            'class': 'w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-900 transition',
        }),
        error_messages={'required': 'Please enter your full name.'}
    )

    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'placeholder': '0300-1234567',
            'class': 'w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-900 transition',
        }),
        error_messages={'required': 'Please enter your phone / WhatsApp number.'}
    )

    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'House / Street Number, Area, Landmark',
            'class': 'w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-900 transition',
        }),
        error_messages={'required': 'Please enter your complete shipping address.'}
    )

    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Karachi, Lahore, Islamabad, Peshawar, etc.',
            'class': 'w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-3 text-sm font-bold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-900 transition',
        }),
        error_messages={'required': 'Please enter your city.'}
    )

    def clean_phone(self):
        """
        Validates Pakistani phone number format.
        Accepts: 03XX-XXXXXXX, 03XXXXXXXXX, +923XXXXXXXXX, 923XXXXXXXXX
        """
        phone = self.cleaned_data['phone'].strip()
        # Remove spaces and dashes for validation
        clean = re.sub(r'[\s\-]', '', phone)

        # Pakistani mobile patterns
        patterns = [
            r'^03\d{9}$',          # 03001234567
            r'^\+923\d{9}$',       # +923001234567
            r'^923\d{9}$',         # 923001234567
        ]

        if not any(re.match(p, clean) for p in patterns):
            raise forms.ValidationError(
                'Please enter a valid Pakistani mobile number (e.g. 0300-1234567).'
            )

        return phone

    def clean_first_name(self):
        """Strip and validate name length."""
        name = self.cleaned_data['first_name'].strip()
        if len(name) < 2:
            raise forms.ValidationError('Name must be at least 2 characters long.')
        return name