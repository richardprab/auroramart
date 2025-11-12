from django import forms
from reviews.models import Review


class ReviewForm(forms.ModelForm):
    """Form for submitting and editing product reviews"""
    
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'rating-input',
            'type': 'hidden',
        })
    )
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Summarize your experience'
        })
    )
    
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Share your thoughts about this product',
            'rows': 4
        })
    )
    
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment']

