from django import forms


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

