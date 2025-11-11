import os
import argparse
import random
from decimal import Decimal
from pathlib import Path
import urllib.request
import csv

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auroramartproject.settings")
import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402
from django.utils.text import slugify  # noqa: E402
from django.apps import apps  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402

Category = apps.get_model("products", "Category")
Product = apps.get_model("products", "Product")
ProductImage = apps.get_model("products", "ProductImage")
ProductVariant = apps.get_model("products", "ProductVariant")
User = apps.get_model("accounts", "User")
Customer = apps.get_model("accounts", "Customer")
Staff = apps.get_model("accounts", "Staff")

RNG = random.Random(42)

# Use royalty‑free images (Unsplash/Pexels)
# Matching IS2108 dataset: 12 categories with subcategories
CATEGORIES = [
    (
        "Electronics",
        ["Smartphones", "Laptops", "Tablets", "Smartwatches", "Cameras", "Headphones", "Monitors", "Printers", "Smart Home"],
        [
            "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9",  # iPhone
            "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed",  # MacBook
            "https://images.unsplash.com/photo-1585790050230-5dd28404f869",  # iPad
            "https://images.unsplash.com/photo-1523275335684-37898b6baf30",  # Smartwatch
            "https://images.unsplash.com/photo-1516035069371-29a1b244cc32",  # Camera
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e",  # Headphones
            "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf",  # Monitor
            "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6",  # Printer
            "https://images.unsplash.com/photo-1558089687-18d4b7a7a0c3",  # Smart speaker
        ],
    ),
    (
        "Fashion - Men",
        ["Tops", "Bottoms", "Footwear", "Outerwear", "Accessories"],
        [
            "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab",  # Men's t-shirt
            "https://images.unsplash.com/photo-1473966968600-fa801b869a1a",  # Men's jeans
            "https://images.unsplash.com/photo-1542291026-7eec264c27ff",  # Men's sneakers
            "https://images.unsplash.com/photo-1551028719-00167b16eac5",  # Men's jacket
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62",  # Watch/accessories
        ],
    ),
    (
        "Fashion - Women",
        ["Tops", "Bottoms", "Dresses", "Outerwear", "Footwear", "Handbags", "Accessories"],
        [
            "https://images.unsplash.com/photo-1485230895905-ec40ba36b9bc",  # Women's blouse
            "https://images.unsplash.com/photo-1541099649105-f69ad21f3246",  # Women's jeans
            "https://images.unsplash.com/photo-1595777457583-95e059d581b8",  # Dress
            "https://images.unsplash.com/photo-1539533018447-63fcce2678e3",  # Women's coat
            "https://images.unsplash.com/photo-1543163521-1bf539c55dd2",  # Women's shoes
            "https://images.unsplash.com/photo-1590874103328-eac38a683ce7",  # Handbag
            "https://images.unsplash.com/photo-1611652022419-a9419f74343d",  # Jewelry
        ],
    ),
    (
        "Home & Kitchen",
        ["Cookware", "Small Appliances", "Bedding", "Home Decor", "Storage & Organization", "Vacuum & Cleaning"],
        [
            "https://images.unsplash.com/photo-1584990347449-39b4aa0aa7ac",  # Cookware
            "https://images.unsplash.com/photo-1585659722983-3a675dabf23d",  # Blender
            "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af",  # Bedding
            "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15",  # Home decor
            "https://images.unsplash.com/photo-1600210491892-03d54c0aaf87",  # Storage boxes
            "https://images.unsplash.com/photo-1558317374-067fb5f30001",  # Vacuum
        ],
    ),
    (
        "Sports & Outdoors",
        ["Fitness Equipment", "Yoga & Wellness", "Cycling", "Camping & Hiking", "Team Sports"],
        [
            "https://images.unsplash.com/photo-1517836357463-d25dfeac3438",  # Gym equipment
            "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b",  # Yoga mat
            "https://images.unsplash.com/photo-1485965120184-e220f721d03e",  # Bicycle
            "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4",  # Camping tent
            "https://images.unsplash.com/photo-1579952363873-27f3bade9f55",  # Basketball
        ],
    ),
    (
        "Beauty & Personal Care",
        ["Skincare", "Makeup", "Hair Care", "Fragrances", "Grooming Tools"],
        [
            "https://images.unsplash.com/photo-1556228720-195a672e8a03",  # Skincare products
            "https://images.unsplash.com/photo-1512496015851-a90fb38ba796",  # Makeup
            "https://images.unsplash.com/photo-1527799820374-dcf8d9d4a388",  # Hair products
            "https://images.unsplash.com/photo-1541643600914-78b084683601",  # Perfume
            "https://images.unsplash.com/photo-1503342394128-c104d54dba01",  # Grooming tools
        ],
    ),
    (
        "Health",
        ["Supplements", "Personal Care", "First Aid", "Medical Devices"],
        [
            "https://images.unsplash.com/photo-1550572017-4870c1e0a6f1",  # Supplements
            "https://images.unsplash.com/photo-1505751172876-fa1923c5c528",  # Pills/vitamins
            "https://images.unsplash.com/photo-1603398938378-e54eab446dde",  # First aid kit
            "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae",  # Thermometer
        ],
    ),
    (
        "Groceries & Gourmet",
        ["Snacks", "Beverages", "Breakfast", "Pantry Staples", "Health Foods"],
        [
            "https://images.unsplash.com/photo-1599490659213-e2b9527bd087",  # Snacks
            "https://images.unsplash.com/photo-1544145945-35c645ddc1d8",  # Coffee/beverages
            "https://images.unsplash.com/photo-1525351484163-7529414344d8",  # Breakfast cereal
            "https://images.unsplash.com/photo-1586201375761-83865001e31c",  # Pantry items
            "https://images.unsplash.com/photo-1490818387583-1baba5e638af",  # Fresh produce
        ],
    ),
    (
        "Toys & Games",
        ["Action Figures", "Building Sets", "Board Games", "Puzzles", "STEM Toys"],
        [
            "https://images.unsplash.com/photo-1599669454699-248893623440",  # Action figures
            "https://images.unsplash.com/photo-1587654780291-39c9404d746b",  # LEGO
            "https://images.unsplash.com/photo-1606167668584-78701c57f13d",  # Board game
            "https://images.unsplash.com/photo-1587731556938-38755b4803a6",  # Puzzle
            "https://images.unsplash.com/photo-1558618666-fcd25c85cd64",  # Robot toy
        ],
    ),
    (
        "Books",
        ["Fiction", "Non-Fiction", "Children", "Comics & Manga", "Textbooks"],
        [
            "https://images.unsplash.com/photo-1544947950-fa07a98d237f",  # Books stack
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d",  # Open book
            "https://images.unsplash.com/photo-1503676260728-1c00da094a0b",  # Children's books
            "https://images.unsplash.com/photo-1612036782180-6f0b6cd846fe",  # Comics
            "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8",  # Textbooks
        ],
    ),
    (
        "Automotive",
        ["Car Care", "Tools & Equipment", "Interior Accessories", "Exterior Accessories", "Oils & Fluids"],
        [
            "https://images.unsplash.com/photo-1601362840469-51e4d8d58785",  # Car cleaning
            "https://images.unsplash.com/photo-1530124566582-a618bc2615dc",  # Tools
            "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f",  # Car interior
            "https://images.unsplash.com/photo-1503376780353-7e6692767b70",  # Car exterior
            "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3",  # Engine/oils
        ],
    ),
    (
        "Pet Supplies",
        ["Dog", "Cat", "Small Pets", "Aquatic", "Accessories"],
        [
            "https://images.unsplash.com/photo-1587300003388-59208cc962cb",  # Dog supplies
            "https://images.unsplash.com/photo-1529257414772-1960b7bea4eb",  # Cat supplies
            "https://images.unsplash.com/photo-1425082661705-1834bfd09dca",  # Hamster
            "https://images.unsplash.com/photo-1520990269108-4f2693f2b621",  # Fish tank
            "https://images.unsplash.com/photo-1548681528-6a5c45b66b42",  # Pet accessories
        ],
    ),
]

# Brand data matching IS2108 categories
BRANDS = {
    "Electronics": ["Samsung", "Apple", "Sony", "LG", "Dell", "HP", "Canon", "Nikon"],
    "Fashion - Men": ["Nike", "Adidas", "Levi's", "Tommy Hilfiger", "Ralph Lauren"],
    "Fashion - Women": ["Zara", "H&M", "Forever 21", "Mango", "ASOS"],
    "Home & Kitchen": ["IKEA", "West Elm", "Crate & Barrel", "KitchenAid", "Cuisinart"],
    "Sports & Outdoors": ["Under Armour", "Reebok", "Puma", "New Balance", "The North Face"],
    "Beauty & Personal Care": ["L'Oréal", "Maybelline", "Neutrogena", "Dove", "Olay"],
    "Health": ["Nature Made", "Centrum", "GNC", "NOW Foods", "Garden of Life"],
    "Groceries & Gourmet": ["Snackify", "GreenGrocer", "BlueCedar", "PurePlate"],
    "Toys & Games": ["LEGO", "Hasbro", "Mattel", "Fisher-Price", "Melissa & Doug"],
    "Books": ["Penguin", "HarperCollins", "Simon & Schuster", "Random House"],
    "Automotive": ["Bosch", "Armor All", "Michelin", "Castrol", "3M"],
    "Pet Supplies": ["Purina", "Blue Buffalo", "Wellness", "Royal Canin", "KONG"],
}

# Colors and sizes
COLORS = ["Black", "White", "Blue", "Red", "Gray", "Navy", "Green"]
SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

# User demographic data options
AGE_RANGES = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
GENDERS = ["Male", "Female", "Other"]
OCCUPATIONS = ["Tech", "Sales", "Service", "Admin", "Education", "Skilled Trades", "Healthcare", "Finance", "Other"]
EDUCATION_LEVELS = ["Secondary", "Diploma", "Bachelor", "Master", "Doctorate"]
INCOME_RANGES = ["Under $30k", "$30k-$50k", "$50k-$75k", "$75k-$100k", "Over $100k"]
EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Self-employed", "Student", "Retired"]


def base_price_for(category_name: str) -> tuple[int, int]:
    ranges = {
        "Electronics": (199, 1299),
        "Fashion - Men": (20, 150),
        "Fashion - Women": (20, 180),
        "Home & Kitchen": (15, 350),
        "Sports & Outdoors": (20, 300),
        "Beauty & Personal Care": (10, 120),
        "Health": (15, 150),
        "Groceries & Gourmet": (3, 80),
        "Toys & Games": (10, 150),
        "Books": (8, 60),
        "Automotive": (15, 250),
        "Pet Supplies": (12, 100),
    }
    return ranges.get(category_name, (10, 200))


def download_image(url: str, filename: str) -> ContentFile:
    try:
        # Unsplash supports size params; keep it light
        if "images.unsplash.com" in url and "w=" not in url:
            url = url + "?auto=format&fit=crop&w=1200&q=70"
        with urllib.request.urlopen(url, timeout=20) as resp:
            return ContentFile(resp.read(), name=filename)
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        # 1x1 transparent PNG fallback
        import base64

        ph = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
        return ContentFile(base64.b64decode(ph), name=f"{filename}.png")


def ensure_product_image(product, image_urls: list):
    img = product.images.order_by("display_order").first()
    if img:
        return img
    # Fallback to a generic image if image_urls is empty
    if not image_urls:
        image_urls = [
            "https://images.unsplash.com/photo-1519125323398-675f0ddb6308?auto=format&fit=crop&w=1200&q=70"
        ]
    url = RNG.choice(image_urls)
    img = ProductImage(
        product=product,
        is_primary=True,
        display_order=0,
        alt_text=f"{product.name} image",
    )
    filename = f"{product.slug or slugify(product.name)}-main.jpg"
    img_file = download_image(url, filename)
    img.image.save(filename, img_file, save=True)
    return img


def unique_value(model, field: str, base: str) -> str:
    """Ensure unique slug/SKU by appending -2, -3, ... if needed."""
    value = base
    n = 2
    while model.objects.filter(**{field: value}).exists():
        value = f"{base}-{n}"
        n += 1
    return value


def product_defaults(name: str, cat, parent_cat, idx: int) -> dict:
    base_slug = slugify(name)
    slug = unique_value(Product, "slug", base_slug)
    
    # Generate SKU in format matching the ML model: XXX-YYYYYYYY (12 chars total)
    # XXX = 3-letter category code, YYYYYYYY = 8 random alphanumeric characters
    import string
    category_code = cat.name[:3].upper().ljust(3, 'X')  # Ensure 3 chars
    random_part = ''.join(RNG.choices(string.ascii_uppercase + string.digits, k=8))
    base_sku = f"{category_code}-{random_part}"
    sku = unique_value(Product, "sku", base_sku)

    # Get brand for this category
    brand_list = BRANDS.get(parent_cat.name, ["Generic"])
    brand = RNG.choice(brand_list)

    return {
        "name": name,
        "slug": slug,
        "sku": sku,
        "category": cat,
        "brand": brand,
        "description": f"High‑quality {name} with modern design and reliable performance.",
        "is_active": True,
    }


def create_sample_users():
    """Create users from b2c_customers_100.csv file"""
    
    csv_path = Path(__file__).parent / "data" / "b2c_customers_100.csv"
    
    if not csv_path.exists():
        print(f"  ERROR: CSV file not found at {csv_path}")
        return 0
    
    # Sample first names and last names for generating user data
    first_names = [
        "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn",
        "Sam", "Cameron", "Dakota", "Skyler", "Blake", "Sage", "River", "Phoenix",
        "Jamie", "Drew", "Kai", "Rowan", "Finley", "Hayden", "Reese", "Emery",
        "Sage", "Parker", "Quinn", "Blake", "Avery", "Riley", "Jordan", "Taylor"
    ]
    
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas",
        "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris",
        "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "King"
    ]
    
    created_count = 0
    skipped_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for idx, row in enumerate(reader, start=1):
            # Skip empty rows
            if not row.get('age') or not row.get('age').strip():
                continue
            
            # Parse CSV data
            age = int(row['age']) if row['age'] else None
            gender = row['gender'] if row['gender'] else None
            employment_status = row['employment_status'] if row['employment_status'] else None
            occupation = row['occupation'] if row['occupation'] else None
            education = row['education'] if row['education'] else None
            household_size = int(row['household_size']) if row['household_size'] else None
            has_children = bool(int(row['has_children'])) if row['has_children'] else None
            monthly_income_sgd = Decimal(row['monthly_income_sgd']) if row['monthly_income_sgd'] else None
            
            username = f"user_{idx:03d}"
            email = f"user{idx:03d}@auroramart.com"
            
            if gender == "Male":
                first_name = RNG.choice(["James", "John", "Robert", "Michael", "William", "David", 
                                        "Richard", "Joseph", "Thomas", "Charles", "Daniel", "Matthew"])
            elif gender == "Female":
                first_name = RNG.choice(["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara",
                                        "Susan", "Jessica", "Sarah", "Karen", "Nancy", "Lisa"])
            else:
                first_name = RNG.choice(first_names)
            
            last_name = RNG.choice(last_names)
            
            # Generate phone number (optional field)
            phone = f"+65{RNG.randint(8000, 9999)}{RNG.randint(1000, 9999)}"
            
            # Check if user already exists
            from accounts.models import Customer, Staff, Superuser
            if (Customer.objects.filter(username=username).exists() or Customer.objects.filter(email=email).exists() or
                Staff.objects.filter(username=username).exists() or Staff.objects.filter(email=email).exists() or
                Superuser.objects.filter(username=username).exists() or Superuser.objects.filter(email=email).exists()):
                skipped_count += 1
                continue
            
            # Create customer (Customer extends User via multi-table inheritance)
            try:
                user = Customer.objects.create_user(
                    username=username,
                    email=email,
                    password="Pass1234",
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    age=age,
                    gender=gender,
                    employment_status=employment_status,
                    occupation=occupation,
                    education=education,
                    household_size=household_size,
                    has_children=has_children,
                    monthly_income_sgd=monthly_income_sgd,
                )
                created_count += 1
                if created_count % 10 == 0:
                    print(f"  Created {created_count} users...")
            except Exception as e:
                print(f"  ERROR creating user {username}: {e}")
                skipped_count += 1
                continue
    
    print(f"Created {created_count} users from CSV")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} users (already exist or error)")
    print()
    return created_count


def create_staff_user():
    """
    Create a staff user with username 'staff_01'.
    """
    print("\n" + "=" * 60)
    print("CREATING STAFF USER")
    print("=" * 60)
    
    username = "staff_01"
    email = "staff_01@auroramart.com"
    
    # Check if user already exists
    if Staff.objects.filter(username=username).exists():
        print(f"Staff user '{username}' already exists. Skipping...")
        return Staff.objects.get(username=username)
    
    # Create staff user (Staff extends User via multi-table inheritance)
    try:
        staff_user = Staff.objects.create_user(
            username=username,
            email=email,
            password="Pass1234",
            first_name="Staff",
            last_name="User",
            permissions='all',  # Default: all permissions
            is_staff=True,
            is_superuser=False,
        )
        print(f"✅ Created staff user: {username} (email: {email})")
        return staff_user
    except Exception as e:
        print(f"❌ Error creating staff user: {e}")
        return None


def create_nus_computing_tshirt():
    """
    Create NUS Computing t-shirt with multiple variants (different colors and sizes with different prices).
    """
    print("\n" + "=" * 60)
    print("CREATING NUS COMPUTING T-SHIRT")
    print("=" * 60)
    
    # Get or create Fashion - Men category and Tops subcategory
    parent_cat, _ = Category.objects.get_or_create(
        name="Fashion - Men",
        defaults={"slug": slugify("Fashion - Men"), "is_active": True}
    )
    subcat, _ = Category.objects.get_or_create(
        name="Tops",
        parent=parent_cat,
        defaults={"slug": slugify("Tops"), "is_active": True}
    )
    
    # Product details
    product_name = "NUS Computing Shirt"
    product_sku = "NUS-COMP-001"
    product_slug = slugify(product_name)
    
    # Check if product already exists (check by SKU or old name)
    existing_product = None
    if Product.objects.filter(sku=product_sku).exists():
        existing_product = Product.objects.get(sku=product_sku)
    elif Product.objects.filter(name="NUS Computing").exists():
        existing_product = Product.objects.get(name="NUS Computing")
    
    if existing_product:
        product = existing_product
        # Update name if it's the old name
        if product.name != product_name:
            product.name = product_name
            product.slug = product_slug
            product.save()
        print(f"Product '{product_name}' already exists. Updating...")
    else:
        # Create product
        product = Product.objects.create(
            sku=product_sku,
            name=product_name,
            slug=product_slug,
            category=subcat,
            brand="NUS",
            description="Official NUS Computing t-shirt. Made from premium cotton blend for comfort and durability. Perfect for students, alumni, and computing enthusiasts.",
            rating=Decimal("4.5"),
            reorder_quantity=10,
            is_active=True,
        )
        print(f"✅ Created product: {product_name} (SKU: {product_sku})")
    
    # Add product image (using a t-shirt image)
    if product.images.count() == 0:
        image_url = "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=1200&q=70"
        img = ProductImage(
            product=product,
            is_primary=True,
            display_order=0,
            alt_text=f"{product_name} image",
        )
        filename = f"{product_slug}-main.jpg"
        img.image.save(filename, download_image(image_url, filename), save=True)
        print(f"  → Added product image")
    
    # Delete existing variants to recreate them
    ProductVariant.objects.filter(product=product).delete()
    
    # Create variants with different colors, sizes, and prices
    # Base price varies by size: XS/S = $25, M/L = $28, XL/XXL = $30
    # Different colors may have slight price variations
    variants_data = [
        # Black variants
        {"color": "Black", "size": "XS", "base_price": 25.00},
        {"color": "Black", "size": "S", "base_price": 25.00},
        {"color": "Black", "size": "M", "base_price": 28.00},
        {"color": "Black", "size": "L", "base_price": 28.00},
        {"color": "Black", "size": "XL", "base_price": 30.00},
        {"color": "Black", "size": "XXL", "base_price": 30.00},
        # White variants
        {"color": "White", "size": "XS", "base_price": 25.00},
        {"color": "White", "size": "S", "base_price": 25.00},
        {"color": "White", "size": "M", "base_price": 28.00},
        {"color": "White", "size": "L", "base_price": 28.00},
        {"color": "White", "size": "XL", "base_price": 30.00},
        {"color": "White", "size": "XXL", "base_price": 30.00},
        # Navy variants (slightly more expensive)
        {"color": "Navy", "size": "XS", "base_price": 26.00},
        {"color": "Navy", "size": "S", "base_price": 26.00},
        {"color": "Navy", "size": "M", "base_price": 29.00},
        {"color": "Navy", "size": "L", "base_price": 29.00},
        {"color": "Navy", "size": "XL", "base_price": 31.00},
        {"color": "Navy", "size": "XXL", "base_price": 31.00},
        # Red variants
        {"color": "Red", "size": "XS", "base_price": 25.00},
        {"color": "Red", "size": "S", "base_price": 25.00},
        {"color": "Red", "size": "M", "base_price": 28.00},
        {"color": "Red", "size": "L", "base_price": 28.00},
        {"color": "Red", "size": "XL", "base_price": 30.00},
        {"color": "Red", "size": "XXL", "base_price": 30.00},
    ]
    
    created_variants = 0
    for idx, variant_data in enumerate(variants_data):
        color = variant_data["color"]
        size = variant_data["size"]
        base_price = Decimal(str(variant_data["base_price"]))
        
        # Add some random variation to prices (±$1)
        price_variation = Decimal(str(RNG.choice([-1, 0, 1])))
        price = base_price + price_variation
        
        # Some variants have compare_price (on sale)
        compare_price = None
        if RNG.random() > 0.6:  # 40% chance of being on sale
            compare_price = price + Decimal(str(RNG.choice([5, 10, 15])))
        
        # Stock varies by size (larger sizes have less stock)
        stock_map = {"XS": 50, "S": 80, "M": 100, "L": 100, "XL": 60, "XXL": 30}
        stock = stock_map.get(size, 50)
        
        # Create variant SKU
        variant_sku = f"{product_sku}-{color}-{size}"
        
        # Check if variant already exists
        if ProductVariant.objects.filter(sku=variant_sku).exists():
            continue
        
        # Create variant
        variant = ProductVariant.objects.create(
            product=product,
            sku=variant_sku,
            color=color,
            size=size,
            price=price,
            compare_price=compare_price,
            stock=stock,
            is_active=True,
            is_default=(idx == 0),  # First variant is default
        )
        created_variants += 1
        
        sale_text = f" (was ${compare_price})" if compare_price else ""
        print(f"  → Created variant: {color} / {size} - ${price}{sale_text} (Stock: {stock}, SKU: {variant_sku})")
    
    print(f"✅ Created {created_variants} variants for {product_name}")
    return product


def seed_from_csv(csv_path, reset=True):
    """
    Seed database from CSV file.
    By default, deletes all existing data before seeding (reset=True).
    """
    if reset:
        print("\n" + "=" * 60)
        print("RESETTING DATABASE BEFORE SEEDING")
        print("=" * 60)
        
        # Get all models
        from django.contrib.sessions.models import Session
        from django.contrib.admin.models import LogEntry
        
        Order = apps.get_model("orders", "Order")
        OrderItem = apps.get_model("orders", "OrderItem")
        Cart = apps.get_model("cart", "Cart")
        CartItem = apps.get_model("cart", "CartItem")
        Wishlist = apps.get_model("accounts", "Wishlist")
        ChatConversation = apps.get_model("chat", "ChatConversation")
        ChatMessage = apps.get_model("chat", "ChatMessage")
        Notification = apps.get_model("notifications", "Notification")
        BrowsingHistory = apps.get_model("accounts", "BrowsingHistory")
        Address = apps.get_model("accounts", "Address")
        SaleSubscription = apps.get_model("accounts", "SaleSubscription")
        Review = apps.get_model("products", "Review")
        Coupon = apps.get_model("adminpanel", "Coupon")
        HomepageBanner = apps.get_model("adminpanel", "HomepageBanner")
        
        # Delete in correct order respecting foreign key constraints
        # Order: child records first, then parent records
        
        print("Deleting sessions and admin logs...")
        Session.objects.all().delete()
        LogEntry.objects.all().delete()
        
        print("Deleting notifications...")
        Notification.objects.all().delete()
        
        print("Deleting order items (child)...")
        OrderItem.objects.all().delete()
        
        print("Deleting orders (parent)...")
        Order.objects.all().delete()
        
        print("Deleting cart items (child)...")
        CartItem.objects.all().delete()
        
        print("Deleting carts (parent)...")
        Cart.objects.all().delete()
        
        print("Deleting chat messages (child)...")
        ChatMessage.objects.all().delete()
        
        print("Deleting chat conversations (parent)...")
        ChatConversation.objects.all().delete()
        
        print("Deleting wishlists...")
        Wishlist.objects.all().delete()
        
        print("Deleting browsing history...")
        BrowsingHistory.objects.all().delete()
        
        print("Deleting sale subscriptions...")
        SaleSubscription.objects.all().delete()
        
        print("Deleting addresses...")
        Address.objects.all().delete()
        
        print("Deleting reviews (depends on User and Product)...")
        Review.objects.all().delete()
        
        print("Deleting coupons (depends on User)...")
        Coupon.objects.all().delete()
        
        print("Deleting homepage banners...")
        HomepageBanner.objects.all().delete()
        
        print("Deleting product images (child)...")
        ProductImage.objects.all().delete()
        
        print("Deleting product variants (child)...")
        ProductVariant.objects.all().delete()
        
        print("Deleting products (parent)...")
        Product.objects.all().delete()
        
        print("Deleting categories (delete children first)...")
        Category.objects.filter(parent__isnull=False).delete()
        Category.objects.filter(parent__isnull=True).delete()
        
        print("Skipping user deletion (avoids complex FK constraints)...")
        # Note: We keep users to avoid FK constraint issues
        # create_sample_users() uses get_or_create(), so it will handle existing users
        
        print("✅ Database reset complete!\n")
    
    create_sample_users()
    
    # Create staff user
    create_staff_user()
    
    # Create NUS Computing t-shirt
    create_nus_computing_tshirt()
    
    with transaction.atomic():
        # Cache for categories
        category_cache = {}

    # Try reading CSV with utf-8-sig, fallback to latin1 if error
    try:
        csvfile = open(csv_path, newline='', encoding='utf-8-sig')
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        csvfile.close()
    except UnicodeDecodeError:
        print("WARNING: utf-8-sig decode failed, trying latin1 encoding.")
        csvfile = open(csv_path, newline='', encoding='latin1')
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        csvfile.close()

    for idx, row in enumerate(rows):
        sku = row.get("SKU code")
        name = row.get("Product name")
        description = row.get("Product description") or f"High-quality {name}."
        parent_cat_name = row.get("Product Category")
        subcat_name = row.get("Product Subcategory")
        price = Decimal(row.get("Unit price") or RNG.randint(10, 100))
        stock = int(row.get("Quantity on hand") or RNG.randint(10, 100))
        reorder_qty = int(row.get("Reorder Quantity") or RNG.randint(5, 20))
        rating = Decimal(row.get("Product rating") or round(RNG.uniform(3.8, 5.0), 1))

        # Create parent category
        if parent_cat_name not in category_cache:
            parent_cat, _ = Category.objects.get_or_create(
                name=parent_cat_name,
                defaults={"slug": slugify(parent_cat_name), "parent": None, "is_active": True}
            )
            category_cache[parent_cat_name] = parent_cat
        else:
            parent_cat = category_cache[parent_cat_name]

        # Create subcategory
        if subcat_name:
            subcat_key = f"{parent_cat_name}:{subcat_name}"
            if subcat_key not in category_cache:
                subcat, _ = Category.objects.get_or_create(
                    name=subcat_name,
                    defaults={"slug": slugify(subcat_name), "parent": parent_cat, "is_active": True}
                )
                category_cache[subcat_key] = subcat
            else:
                subcat = category_cache[subcat_key]
        else:
            subcat = parent_cat

        # Brand random from parent category brands or "Generic"
        brand_list = BRANDS.get(parent_cat_name, ["Generic"])
        brand = RNG.choice(brand_list)

        slug = unique_value(Product, "slug", slugify(name))
        product, created = Product.objects.get_or_create(
            sku=sku,
            defaults={
                "name": name,
                "slug": slug,
                "category": subcat,
                "brand": brand,
                "description": description,
                "rating": rating,
                    "reorder_quantity": reorder_qty,
                "is_active": True,
            }
        )
        if created:
            print(f"Created product: {product.name} (SKU: {sku}, Brand: {brand})")
        else:
            product.category = subcat
            product.brand = brand
            product.description = description
            product.rating = rating
            product.reorder_quantity = reorder_qty
            product.is_active = True
            product.save()

        # Find image URLs for the product's parent category and subcategory
        image_urls = []
        for cat_name, subcats, urls in CATEGORIES:
            if cat_name == parent_cat_name:
                image_urls = urls
                break
        ensure_product_image(product, image_urls)

        # Create variants for ALL products (required for products to show up)
        if product.variants.count() == 0:
            is_fashion = parent_cat_name in ["Fashion - Men", "Fashion - Women"]
            
            if is_fashion:
                # Create variant with color and size for fashion items
                color = RNG.choice(COLORS)
                size = RNG.choice(SIZES)
                variant_sku = unique_value(ProductVariant, "sku", f"{sku}-V")
                ProductVariant.objects.create(
                    product=product,
                    sku=variant_sku,
                    color=color,
                    size=size,
                    price=price,
                    compare_price=price + Decimal(RNG.choice([0, 10, 20, 50, 100])),
                    stock=stock,
                    is_active=True,
                    is_default=True,
                )
                print(f"  → Created variant: {color} / {size} - ${price} (SKU: {variant_sku})")
            else:
                # For non-fashion items, create default variant without color/size
                # Use the same SKU as the product (no variant suffix needed)
                ProductVariant.objects.create(
                    product=product,
                    sku=sku,  # Same SKU as product
                    color="",  # No color for non-fashion
                    size="",   # No size for non-fashion
                    price=price,
                    compare_price=price + Decimal(RNG.choice([0, 10, 20, 50, 100])) if RNG.random() > 0.5 else None,
                    stock=stock,
                    is_active=True,
                    is_default=True,
                )
                print(f"  → Created default variant - ${price} (SKU: {sku})")

    print(
        f"\nDone. Categories: {Category.objects.count()}, Products: {Product.objects.count()}, Variants: {ProductVariant.objects.count()}"
    )


def delete_all_data():
    """
    Delete all data from the database (but keep the database file and structure).
    Useful for resetting the database to a clean state.
    """
    print("=" * 60)
    print("DELETING ALL DATA FROM DATABASE")
    print("=" * 60)
    
    # Get all models
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.sessions.models import Session
    from django.contrib.admin.models import LogEntry
    
    Order = apps.get_model("orders", "Order")
    OrderItem = apps.get_model("orders", "OrderItem")
    Cart = apps.get_model("cart", "Cart")
    CartItem = apps.get_model("cart", "CartItem")
    Wishlist = apps.get_model("accounts", "Wishlist")
    ChatConversation = apps.get_model("chat", "ChatConversation")
    ChatMessage = apps.get_model("chat", "ChatMessage")
    Notification = apps.get_model("notifications", "Notification")
    BrowsingHistory = apps.get_model("accounts", "BrowsingHistory")
    Address = apps.get_model("accounts", "Address")
    SaleSubscription = apps.get_model("accounts", "SaleSubscription")
    Review = apps.get_model("products", "Review")
    Coupon = apps.get_model("adminpanel", "Coupon")
    HomepageBanner = apps.get_model("adminpanel", "HomepageBanner")
    
    with transaction.atomic():
        # Delete in correct order respecting foreign key constraints
        
        print("Deleting sessions and admin logs...")
        Session.objects.all().delete()
        LogEntry.objects.all().delete()
        
        print("Deleting notifications...")
        Notification.objects.all().delete()
        
        print("Deleting order items (child)...")
        OrderItem.objects.all().delete()
        
        print("Deleting orders (parent)...")
        Order.objects.all().delete()
        
        print("Deleting cart items (child)...")
        CartItem.objects.all().delete()
        
        print("Deleting carts (parent)...")
        Cart.objects.all().delete()
        
        print("Deleting chat messages (child)...")
        ChatMessage.objects.all().delete()
        
        print("Deleting chat conversations (parent)...")
        ChatConversation.objects.all().delete()
        
        print("Deleting wishlists...")
        Wishlist.objects.all().delete()
        
        print("Deleting browsing history...")
        BrowsingHistory.objects.all().delete()
        
        print("Deleting sale subscriptions...")
        SaleSubscription.objects.all().delete()
        
        print("Deleting addresses...")
        Address.objects.all().delete()
        
        print("Deleting reviews (depends on User and Product)...")
        Review.objects.all().delete()
        
        print("Deleting coupons (depends on User)...")
        Coupon.objects.all().delete()
        
        print("Deleting homepage banners...")
        HomepageBanner.objects.all().delete()
        
        print("Deleting product images (child)...")
        ProductImage.objects.all().delete()
        
        print("Deleting product variants (child)...")
        ProductVariant.objects.all().delete()
        
        print("Deleting products (parent)...")
        Product.objects.all().delete()
        
        print("Deleting categories (delete children first)...")
        # Delete child categories first (those with parents), then parent categories
        Category.objects.filter(parent__isnull=False).delete()
        Category.objects.filter(parent__isnull=True).delete()
        
        print("Skipping user deletion (avoids complex FK constraints)...")
        # Note: We keep users to avoid FK constraint issues
        # create_sample_users() uses get_or_create(), so it will handle existing users
        
        print("\n✅ All data deleted successfully!")
    print(f"Remaining superusers: {User.objects.filter(is_superuser=True).count()}")
    print("=" * 60)


def delete_database_file():
    """
    Delete the entire database file (db.sqlite3).
    This requires migrations to be run again.
    """
    import sys
    
    print("=" * 60)
    print("WARNING: DELETING DATABASE FILE")
    print("=" * 60)
    print("This will delete the entire db.sqlite3 file.")
    print("You will need to run migrations again:")
    print("  python manage.py migrate")
    print("  python manage.py createsuperuser")
    print("=" * 60)
    
    response = input("Are you sure? Type 'yes' to continue: ")
    if response.lower() != 'yes':
        print("❌ Aborted.")
        sys.exit(0)
    
    db_path = Path(__file__).resolve().parent / "db.sqlite3"
    
    if db_path.exists():
        try:
            os.remove(db_path)
            print(f"\n✅ Database file deleted: {db_path}")
            print("\nNext steps:")
            print("  1. python manage.py migrate")
            print("  2. python manage.py createsuperuser")
            print("  3. python populate_db.py --csv data/b2c_products_500.csv")
        except Exception as e:
            print(f"❌ Error deleting database: {e}")
            sys.exit(1)
    else:
        print(f"⚠️  Database file not found: {db_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Seed catalog from CSV or manage database."
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Don't delete existing data before seeding (default: deletes all data).",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="data/b2c_products_500.csv",
        help="CSV file to import products from.",
    )
    parser.add_argument(
        "--delete-data",
        action="store_true",
        help="Delete all data from database (keeps DB file and structure).",
    )
    parser.add_argument(
        "--delete-db",
        action="store_true",
        help="Delete the entire database file (requires migrations after).",
    )
    args = parser.parse_args()
    
    # Handle delete operations
    if args.delete_db:
        delete_database_file()
        return
    
    if args.delete_data:
        delete_all_data()
        return
    
    # Otherwise, seed from CSV
    # By default, reset=True (delete all data), unless --no-reset is specified
    seed_from_csv(
        csv_path=args.csv,
        reset=not args.no_reset,
    )


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)
    main()


