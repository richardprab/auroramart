import os
import django
import random
import string
import sys

#1. Create a single staff account (auto-increments):
#python adminpanel/create_staff.py
#2. Create multiple staff accounts at once:
#python adminpanel/create_staff.py 5  # Creates 5 staff accounts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auroramartproject.settings")

django.setup()

from accounts.models import User, Staff
from django.db import IntegrityError

def generate_random_password(length=12):
    """Generate a random secure password"""
    characters = string.ascii_letters + string.digits + "!@#$%"
    password = ''.join(random.choice(characters) for i in range(length))
    return password

def get_next_staff_number():
    """Get the next available staff number"""
    # Find all existing staff users with username pattern 'staffXXX'
    staff_users = Staff.objects.filter(username__startswith='staff')
    
    if not staff_users.exists():
        return 1
    
    # Extract numbers from usernames and find the highest
    max_number = 0
    for user in staff_users:
        try:
            # Extract number from username like 'staff001'
            number = int(user.username.replace('staff', ''))
            if number > max_number:
                max_number = number
        except ValueError:
            continue
    
    return max_number + 1

def create_staff_user():
    """
    Creates a single staff user account with auto-generated credentials.
    Returns the created user details.
    """
    
    # Get next staff number
    staff_number = get_next_staff_number()
    
    # Generate staff details
    username = f'staff{staff_number:03d}'  # Format as staff001, staff002, etc.
    email = f'{username}@auroramart.com'
    password = generate_random_password()
    first_name = 'Staff'
    last_name = f'User {staff_number}'
    
    try:
        # Create staff user (Staff extends User via multi-table inheritance)
        # This automatically creates both User and Staff records
        staff_user = Staff.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            permissions='all',  # Default: all permissions
            is_staff=True,
            is_active=True,
        )
        
        print("=" * 50)
        print("✅ Staff Account Created Successfully!")
        print("=" * 50)
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Name: {first_name} {last_name}")
        print("=" * 50)
        print("\n⚠️  IMPORTANT: Save these credentials securely!")
        print("The password cannot be retrieved later.\n")
        
        return {
            'username': username,
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
        }
        
    except IntegrityError as e:
        print(f"❌ Error: Unable to create staff user. {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def create_multiple_staff_users(count=1):
    """
    Create multiple staff users at once.
    
    Args:
        count (int): Number of staff users to create
    """
    print(f"\n📋 Creating {count} staff account(s)...\n")
    
    created_users = []
    
    for _ in range(count):
        user_data = create_staff_user()
        if user_data:
            created_users.append(user_data)
        print()  # Add spacing between users
    
    # Summary
    print("=" * 50)
    print(f"✅ Successfully created {len(created_users)} staff account(s)")
    print("=" * 50)
    
    if created_users:
        print("\n📝 Summary of Created Accounts:")
        print("-" * 50)
        for user_data in created_users:
            print(f"Username: {user_data['username']} | Password: {user_data['password']}")
        print()
    
    return created_users

if __name__ == '__main__':
    # Check if user wants to create multiple accounts
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
            create_multiple_staff_users(count)
        except ValueError:
            print("❌ Error: Please provide a valid number")
            print("Usage: python adminpanel/create_staff.py [number_of_accounts]")
    else:
        # Create single staff account
        create_staff_user()