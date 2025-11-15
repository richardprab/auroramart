from django import forms
from vouchers.models import Voucher
from accounts.models import Staff


class ProductSearchForm(forms.Form):
    """Form for searching products by name or SKU"""
    
    query = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(
            attrs={
                'class': 'search-input',
                'placeholder': 'Search by product name or SKU (e.g., iPhone, PHO-0001)...',
                'autocomplete': 'off',
                'id': 'searchInput',
            }
        ),
        label='',
        help_text='',
    )
    
    def clean_query(self):
        """Clean and normalize the search query"""
        query = self.cleaned_data.get('query', '').strip()
        return query


class OrderSearchForm(forms.Form):
    """Form for searching orders by order number or customer username"""
    
    query = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(
            attrs={
                'class': 'search-input',
                'placeholder': 'Search by order number (e.g., ORD-A1B2C3D4) or customer username (e.g., testcustomer)...',
                'autocomplete': 'off',
                'id': 'searchInput',
            }
        ),
        label='',
        help_text='',
    )
    
    def clean_query(self):
        """Clean and normalize the search query"""
        query = self.cleaned_data.get('query', '').strip()
        return query


class VoucherForm(forms.ModelForm):
    """Form for creating and editing vouchers"""
    
    class Meta:
        model = Voucher
        fields = [
            'name', 'promo_code', 'description', 'discount_type', 'discount_value',
            'max_discount', 'min_purchase', 'first_time_only', 'exclude_sale_items',
            'max_uses', 'max_uses_per_user', 'start_date', 'end_date', 'is_active',
            'user'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500', 'required': True}),
            'promo_code': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500', 'required': True}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500', 'rows': 3}),
            'discount_type': forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'}),
            'discount_value': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500', 'step': '0.01', 'required': True}),
            'max_discount': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500', 'step': '0.01'}),
            'min_purchase': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500', 'step': '0.01', 'value': '0'}),
            'first_time_only': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'}),
            'exclude_sale_items': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'}),
            'max_uses': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'}),
            'max_uses_per_user': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500', 'value': '1', 'required': True}),
            'start_date': forms.DateTimeInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500', 'type': 'datetime-local', 'required': True}),
            'end_date': forms.DateTimeInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500', 'type': 'datetime-local', 'required': True}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'}),
            'user': forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make user field optional
        self.fields['user'].required = False
        self.fields['user'].queryset = self.fields['user'].queryset.order_by('username')


class StaffSearchForm(forms.Form):
    """Form for searching staff by username or email"""
    
    query = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(
            attrs={
                'class': 'search-input',
                'placeholder': 'Search by username or email...',
                'autocomplete': 'off',
                'id': 'searchInput',
            }
        ),
        label='',
        help_text='',
    )
    
    def clean_query(self):
        """Clean and normalize the search query"""
        query = self.cleaned_data.get('query', '').strip()
        return query


class StaffPermissionForm(forms.ModelForm):
    """Form for editing staff permissions"""
    
    class Meta:
        model = Staff
        fields = ['permissions']
        widgets = {
            'permissions': forms.Select(
                attrs={
                    'class': 'form-control',
                    'style': 'width: 100%; padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 0.5rem;'
                }
            )
        }


class CustomerSearchForm(forms.Form):
    """Form for searching customers by username, email, or name"""
    
    query = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(
            attrs={
                'class': 'search-input',
                'placeholder': 'Search by username, email, or name (e.g., john, john@example.com)...',
                'autocomplete': 'off',
                'id': 'searchInput',
            }
        ),
        label='',
        help_text='',
    )
    
    def clean_query(self):
        """Clean and normalize the search query"""
        query = self.cleaned_data.get('query', '').strip()
        return query

