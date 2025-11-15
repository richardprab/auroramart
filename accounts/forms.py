from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Address, Customer
import re

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form with enhanced validation"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "your@email.com",
                "autocomplete": "email",
            }
        ),
        help_text="Required. Enter a valid email address.",
        error_messages={
            "required": "Email address is required.",
            "invalid": "Please enter a valid email address.",
        },
    )

    first_name = forms.CharField(
        required=True,  # Changed to required
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your first name",
                "autocomplete": "given-name",
            }
        ),
        help_text="Required. Enter your first name.",
        error_messages={
            "required": "First name is required.",
        },
    )

    last_name = forms.CharField(
        required=True,  # Changed to required
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your last name",
                "autocomplete": "family-name",
            }
        ),
        help_text="Required. Enter your last name.",
        error_messages={
            "required": "Last name is required.",
        },
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        )
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Choose a username",
                    "autocomplete": "username",
                }
            ),
        }
        error_messages = {
            "username": {
                "required": "Username is required.",
                "unique": "This username is already taken.",
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add form-control class and attributes to password fields
        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Create a strong password",
                "autocomplete": "new-password",
            }
        )

        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Re-enter your password",
                "autocomplete": "new-password",
            }
        )

        # Customize username field
        self.fields["username"].help_text = (
            "150 characters or fewer. Letters, digits and @/./+/-/_ only."
        )
        self.fields["username"].error_messages = {
            "required": "Username is required.",
            "unique": "This username is already taken.",
            "invalid": "Username can only contain letters, numbers, and @/./+/-/_ characters.",
        }

        # Customize password fields
        self.fields["password1"].help_text = (
            "Your password must contain at least 8 characters, "
            "cannot be entirely numeric, and cannot be too common."
        )
        self.fields["password1"].error_messages = {
            "required": "Password is required.",
        }

        self.fields["password2"].help_text = (
            "Enter the same password as before, for verification."
        )
        self.fields["password2"].error_messages = {
            "required": "Please confirm your password.",
        }

    def clean_username(self):
        """Validate username"""
        username = self.cleaned_data.get("username")

        if not username:
            raise ValidationError("Username is required.")

        # Check length
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")

        if len(username) > 150:
            raise ValidationError("Username cannot be more than 150 characters.")

        # Check for valid characters
        if not re.match(r"^[\w.@+-]+$", username):
            raise ValidationError(
                "Username can only contain letters, numbers, and @/./+/-/_ characters."
            )

        # Check if username already exists (check Customer, Staff, Superuser)
        from accounts.models import Customer, Staff, Superuser
        if (Customer.objects.filter(username__iexact=username).exists() or
            Staff.objects.filter(username__iexact=username).exists() or
            Superuser.objects.filter(username__iexact=username).exists()):
            raise ValidationError(
                "This username is already taken. Please choose another."
            )

        return username

    def clean_email(self):
        """Validate email"""
        email = self.cleaned_data.get("email")

        if not email:
            raise ValidationError("Email address is required.")

        # Check if email already exists (check Customer, Staff, Superuser)
        from accounts.models import Customer, Staff, Superuser
        if (Customer.objects.filter(email__iexact=email).exists() or
            Staff.objects.filter(email__iexact=email).exists() or
            Superuser.objects.filter(email__iexact=email).exists()):
            raise ValidationError(
                "This email address is already registered. Please use another or try logging in."
            )

        # Validate email format
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, email):
            raise ValidationError("Please enter a valid email address.")

        return email.lower()

    def clean_first_name(self):
        """Validate first name"""
        first_name = self.cleaned_data.get("first_name", "")

        if not first_name:
            raise ValidationError("First name is required.")

        # Remove extra spaces
        first_name = first_name.strip()

        # Check minimum length
        if len(first_name) < 2:
            raise ValidationError("First name must be at least 2 characters long.")

        # Check length
        if len(first_name) > 150:
            raise ValidationError("First name cannot be more than 150 characters.")

        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", first_name):
            raise ValidationError(
                "First name can only contain letters, spaces, hyphens, and apostrophes."
            )

        return first_name.strip()

    def clean_last_name(self):
        """Validate last name"""
        last_name = self.cleaned_data.get("last_name", "")

        if not last_name:
            raise ValidationError("Last name is required.")

        # Remove extra spaces
        last_name = last_name.strip()

        # Check minimum length
        if len(last_name) < 2:
            raise ValidationError("Last name must be at least 2 characters long.")

        # Check length
        if len(last_name) > 150:
            raise ValidationError("Last name cannot be more than 150 characters.")

        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", last_name):
            raise ValidationError(
                "Last name can only contain letters, spaces, hyphens, and apostrophes."
            )

        return last_name.strip()

    def clean_password1(self):
        """Validate password strength"""
        password = self.cleaned_data.get("password1")

        if not password:
            raise ValidationError("Password is required.")

        # Check length
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        # Check if entirely numeric
        if password.isdigit():
            raise ValidationError("Password cannot be entirely numeric.")

        # Check for at least one letter
        if not re.search(r"[a-zA-Z]", password):
            raise ValidationError("Password must contain at least one letter.")

        # Check for common passwords
        common_passwords = [
            "password",
            "12345678",
            "qwerty",
            "abc123",
            "password123",
            "11111111",
            "00000000",
        ]
        if password.lower() in common_passwords:
            raise ValidationError(
                "This password is too common. Please choose a stronger password."
            )

        # Check against username
        username = self.cleaned_data.get("username", "")
        if username and username.lower() in password.lower():
            raise ValidationError("Password cannot contain your username.")

        return password

    def clean_password2(self):
        """Validate password confirmation"""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if not password2:
            raise ValidationError("Please confirm your password.")

        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields must match.")

        return password2

    def save(self, commit=True):
        """Save the user with email and names"""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()

        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile information"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "your@email.com",
                "autocomplete": "email",
            }
        ),
        help_text="Required. Enter a valid email address.",
        error_messages={
            "required": "Email address is required.",
            "invalid": "Please enter a valid email address.",
        },
    )

    first_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your first name",
                "autocomplete": "given-name",
            }
        ),
        help_text="Required. Enter your first name.",
        error_messages={
            "required": "First name is required.",
        },
    )

    last_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your last name",
                "autocomplete": "family-name",
            }
        ),
        help_text="Required. Enter your last name.",
        error_messages={
            "required": "Last name is required.",
        },
    )

    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "+65",
                "autocomplete": "tel",
            }
        ),
        help_text="Optional. Enter your phone number.",
    )

    class Meta:
        model = User
        fields = [
            "first_name", 
            "last_name", 
            "email", 
            "phone",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        """Validate email - allow keeping same email, but prevent duplicates"""
        email = self.cleaned_data.get("email")

        if not email:
            raise ValidationError("Email address is required.")

        # Check if email already exists (excluding current user)
        if self.user:
            from accounts.models import Customer, Staff, Superuser
            # Check across all user types, excluding current user
            existing = (Customer.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists() or
                       Staff.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists() or
                       Superuser.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists())
            if existing:
                raise ValidationError(
                    "This email address is already registered to another account."
                )

        # Validate email format
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, email):
            raise ValidationError("Please enter a valid email address.")

        return email.lower()

    def clean_first_name(self):
        """Validate first name"""
        first_name = self.cleaned_data.get("first_name", "")

        if not first_name:
            raise ValidationError("First name is required.")

        # Remove extra spaces
        first_name = first_name.strip()

        # Check minimum length
        if len(first_name) < 2:
            raise ValidationError("First name must be at least 2 characters long.")

        # Check length
        if len(first_name) > 150:
            raise ValidationError("First name cannot be more than 150 characters.")

        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", first_name):
            raise ValidationError(
                "First name can only contain letters, spaces, hyphens, and apostrophes."
            )

        return first_name.strip()

    def clean_last_name(self):
        """Validate last name"""
        last_name = self.cleaned_data.get("last_name", "")

        if not last_name:
            raise ValidationError("Last name is required.")

        # Remove extra spaces
        last_name = last_name.strip()

        # Check minimum length
        if len(last_name) < 2:
            raise ValidationError("Last name must be at least 2 characters long.")

        # Check length
        if len(last_name) > 150:
            raise ValidationError("Last name cannot be more than 150 characters.")

        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", last_name):
            raise ValidationError(
                "Last name can only contain letters, spaces, hyphens, and apostrophes."
            )

        return last_name.strip()

    def clean_phone(self):
        """Validate phone number"""
        phone = self.cleaned_data.get("phone", "")

        if not phone:
            return ""

        phone = phone.strip()

        # Allow common phone formats
        # Examples: +1234567890, (123) 456-7890, 123-456-7890
        phone_regex = r"^[\+\(\)\-\s\d]+$"
        if not re.match(phone_regex, phone):
            raise ValidationError(
                "Please enter a valid phone number (digits, spaces, +, -, () allowed)."
            )

        # Check length (at least 10 digits)
        digits_only = re.sub(r"\D", "", phone)
        if len(digits_only) < 10:
            raise ValidationError("Phone number must contain at least 10 digits.")

        if len(digits_only) > 15:
            raise ValidationError("Phone number cannot be more than 15 digits.")

        return phone


    def save(self, commit=True):
        """Save the user profile with cleaned data"""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        
        # Phone is only for Customer instances
        phone = self.cleaned_data.get("phone", "").strip()
        if isinstance(user, Customer) or hasattr(user, 'customer'):
            try:
                customer = Customer.objects.get(id=user.id)
                customer.phone = phone
                if commit:
                    customer.save()
            except Customer.DoesNotExist:
                pass

        if commit:
            user.save()
        return user


class AddressForm(forms.ModelForm):
    """Form for managing user addresses"""
    
    address_line1 = forms.CharField(
        required=True,
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Street address, P.O. box, etc.",
                "autocomplete": "street-address",
            }
        ),
        help_text="Street address, P.O. box, etc.",
    )
    
    address_line2 = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Apartment, suite, unit, etc. (Optional)",
                "autocomplete": "address-line2",
            }
        ),
        help_text="Apartment, suite, unit, etc. (Optional)",
    )
    
    city = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "City",
                "autocomplete": "address-level2",
            }
        ),
    )
    
    state = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "State, province, or region",
                "autocomplete": "address-level1",
            }
        ),
    )
    
    postal_code = forms.CharField(
        required=True,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Postal code",
                "autocomplete": "postal-code",
            }
        ),
    )
    
    country = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.Select(
            attrs={
                "class": "form-control",
            },
            choices=[
                ("", "Select Country"),
                ("Singapore", "Singapore"),
                ("Malaysia", "Malaysia"),
                ("Thailand", "Thailand"),
                ("Indonesia", "Indonesia"),
                ("Philippines", "Philippines"),
                ("Vietnam", "Vietnam"),
                ("United States", "United States"),
                ("United Kingdom", "United Kingdom"),
                ("Australia", "Australia"),
            ]
        ),
    )
    
    is_default = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
        help_text="Set as default shipping address",
    )
    
    class Meta:
        model = Address
        fields = [
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
        ]
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # Set address_type to 'shipping' by default
        if not self.instance.pk:
            self.instance.address_type = 'shipping'
            if self.user:
                self.instance.user = self.user
    
    def clean_postal_code(self):
        """Validate postal code"""
        postal_code = self.cleaned_data.get("postal_code", "").strip()
        
        if not postal_code:
            raise ValidationError("Postal code is required.")
        
        # Allow alphanumeric postal codes
        if not re.match(r"^[a-zA-Z0-9\s\-]+$", postal_code):
            raise ValidationError("Postal code can only contain letters, numbers, spaces, and hyphens.")
        
        return postal_code
    
    def save(self, commit=True):
        """Save the address"""
        address = super().save(commit=False)
        
        if self.user:
            address.user = self.user
        
        # Set address_type to shipping if not set
        if not address.address_type:
            address.address_type = 'shipping'
        
        # Set full_name from user if not provided
        if not address.full_name and self.user:
            address.full_name = self.user.get_full_name() or self.user.username
        
        # Set zip_code same as postal_code for compatibility
        address.zip_code = address.postal_code
        
        if commit:
            address.save()
        return address


class CustomerPasswordResetForm(PasswordResetForm):
    """
    Custom password reset form that only allows Customer users to reset passwords.
    This ensures staff/superusers cannot reset passwords through the customer login flow.
    """
    
    def get_users(self, email):
        """
        Override to only return Customer users with the given email.
        """
        active_customers = Customer.objects.filter(
            email__iexact=email,
            is_active=True
        )
        return (u for u in active_customers if u.has_usable_password())
