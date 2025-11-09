import os
import argparse
import random
from decimal import Decimal
from pathlib import Path
import urllib.request

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
    base_sku = f"{cat.name[:3].upper()}-{idx:04d}"
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
        "size_guide": "Refer to the product details for sizing.",
        "rating": Decimal(str(round(RNG.uniform(3.8, 5.0), 1))),
        "review_count": RNG.randint(3, 120),
        "is_featured": (idx % 3 == 0),
        "is_active": True,
    }


@transaction.atomic
def seed(reset: bool = False, per_category: int = 3, variants_per_product: int = 3):
    # Create sample users with demographic data
    create_sample_users()
    
    if reset:
        print("Resetting catalog…")
        ProductVariant.objects.all().delete()
        ProductImage.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()

    for top, subs, image_urls in CATEGORIES:
        parent, _ = Category.objects.get_or_create(
            name=top, defaults={"slug": slugify(top), "parent": None, "is_active": True}
        )
        targets = []
        if subs:
            for s in subs:
                c, _ = Category.objects.get_or_create(
                    name=s,
                    defaults={"slug": slugify(s), "parent": parent, "is_active": True},
                )
                targets.append(c)
        else:
            targets = [parent]

        low, high = base_price_for(parent.name)

        for cat in targets:
            for i in range(1, per_category + 1):
                name = f"{cat.name} Product {i}"
                defaults = product_defaults(name, cat, parent, i)

                # Use slug for lookup so re‑runs don't duplicate by name
                product, created = Product.objects.get_or_create(
                    slug=defaults["slug"], defaults=defaults
                )
                if created:
                    print(f"Created product: {product.name} (Brand: {product.brand})")
                else:
                    # Ensure required fields if product already existed
                    if not product.sku:
                        product.sku = unique_value(
                            Product, "sku", f"{cat.name[:3].upper()}-{i:04d}"
                        )
                    if not product.category_id:
                        product.category = cat
                    if not product.brand:
                        brand_list = BRANDS.get(parent.name, ["Generic"])
                        product.brand = RNG.choice(brand_list)
                    product.save()

                primary_img = ensure_product_image(product, image_urls)

                # Create variants with color, size, price, and stock
                if product.variants.count() == 0:
                    # Check if this is a fashion category (products that have sizes/colors)
                    fashion_categories = ['Fashion - Men', 'Fashion - Women']
                    is_fashion = parent.name in fashion_categories
                    
                    if is_fashion:
                        # Fashion products: multiple variants with colors and sizes
                        product_colors = RNG.sample(
                            COLORS, min(variants_per_product, len(COLORS))
                        )
                        product_sizes = RNG.sample(
                            SIZES, min(variants_per_product, len(SIZES))
                        )

                        for v in range(variants_per_product):
                            base_price = Decimal(RNG.randint(low, high))
                            price = max(
                                base_price + Decimal(RNG.randint(-20, 40)), Decimal("5.00")
                            )
                            compare = price + Decimal(RNG.choice([0, 10, 20, 50, 100]))

                            color = product_colors[v % len(product_colors)]
                            size = product_sizes[v % len(product_sizes)]
                            sku_suffix = f"{color[:3].upper()}-{size}"

                            variant_sku = unique_value(
                                ProductVariant, "sku", f"{product.sku}-{sku_suffix}"
                            )

                            ProductVariant.objects.create(
                                product=product,
                                sku=variant_sku,
                                color=color,
                                size=size,
                                price=price,
                                compare_price=compare if compare > price else None,
                                stock=RNG.randint(0, 80),
                                is_active=True,
                                is_default=(v == 0),
                            )
                            print(f"  → Created variant: {color} / {size} - ${price}")
                    else:
                        # Non-fashion products: single variant without color/size
                        base_price = Decimal(RNG.randint(low, high))
                        compare = base_price + Decimal(RNG.choice([0, 10, 20, 50, 100]))
                        
                        variant_sku = unique_value(
                            ProductVariant, "sku", f"{product.sku}-STD"
                        )
                        
                        ProductVariant.objects.create(
                            product=product,
                            sku=variant_sku,
                            color="",  # No color for non-fashion
                            size="",   # No size for non-fashion
                            price=base_price,
                            compare_price=compare if compare > base_price else None,
                            stock=RNG.randint(5, 100),
                            is_active=True,
                            is_default=True,
                        )
                        print(f"  → Created single variant: ${base_price}")

    print(
        f"\nDone. Categories: {Category.objects.count()}, Products: {Product.objects.count()}, Variants: {ProductVariant.objects.count()}"
    )


def create_sample_users():
    """Create sample users with varied demographic profiles for ML testing"""
    print("\nCreating sample users...")
    
    sample_users = [
        {
            "username": "demo_user",
            "email": "demo@auroramart.com",
            "first_name": "Demo",
            "last_name": "User",
            "age": 28,
            "age_range": "25-34",
            "gender": "Male",
            "household_size": 2,
            "has_children": False,
            "occupation": "Tech",
            "education": "Bachelor",
            "monthly_income": 65000,
            "employment": "Full-time",
            "income_range": "$50k-$75k",
        },
        {
            "username": "sarah_jones",
            "email": "sarah.jones@auroramart.com",
            "first_name": "Sarah",
            "last_name": "Jones",
            "age": 32,
            "age_range": "25-34",
            "gender": "Female",
            "household_size": 4,
            "has_children": True,
            "occupation": "Healthcare",
            "education": "Master",
            "monthly_income": 85000,
            "employment": "Full-time",
            "income_range": "$75k-$100k",
        },
        {
            "username": "mike_chen",
            "email": "mike.chen@auroramart.com",
            "first_name": "Mike",
            "last_name": "Chen",
            "age": 45,
            "age_range": "45-54",
            "gender": "Male",
            "household_size": 3,
            "has_children": True,
            "occupation": "Finance",
            "education": "Master",
            "monthly_income": 120000,
            "employment": "Full-time",
            "income_range": "Over $100k",
        },
        {
            "username": "emma_wilson",
            "email": "emma.wilson@auroramart.com",
            "first_name": "Emma",
            "last_name": "Wilson",
            "age": 22,
            "age_range": "18-24",
            "gender": "Female",
            "household_size": 1,
            "has_children": False,
            "occupation": "Student",
            "education": "Secondary",
            "monthly_income": 15000,
            "employment": "Part-time",
            "income_range": "Under $30k",
        },
        {
            "username": "david_martinez",
            "email": "david.martinez@auroramart.com",
            "first_name": "David",
            "last_name": "Martinez",
            "age": 38,
            "age_range": "35-44",
            "gender": "Male",
            "household_size": 2,
            "has_children": False,
            "occupation": "Sales",
            "education": "Bachelor",
            "monthly_income": 55000,
            "employment": "Full-time",
            "income_range": "$50k-$75k",
        },
        {
            "username": "lisa_taylor",
            "email": "lisa.taylor@auroramart.com",
            "first_name": "Lisa",
            "last_name": "Taylor",
            "age": 58,
            "age_range": "55-64",
            "gender": "Female",
            "household_size": 2,
            "has_children": True,
            "occupation": "Education",
            "education": "Master",
            "monthly_income": 70000,
            "employment": "Full-time",
            "income_range": "$50k-$75k",
        },
        {
            "username": "james_brown",
            "email": "james.brown@auroramart.com",
            "first_name": "James",
            "last_name": "Brown",
            "age": 67,
            "age_range": "65+",
            "gender": "Male",
            "household_size": 2,
            "has_children": True,
            "occupation": "Other",
            "education": "Diploma",
            "monthly_income": 40000,
            "employment": "Retired",
            "income_range": "$30k-$50k",
        },
        {
            "username": "jessica_lee",
            "email": "jessica.lee@auroramart.com",
            "first_name": "Jessica",
            "last_name": "Lee",
            "age": 29,
            "age_range": "25-34",
            "gender": "Female",
            "household_size": 1,
            "has_children": False,
            "occupation": "Tech",
            "education": "Bachelor",
            "monthly_income": 75000,
            "employment": "Full-time",
            "income_range": "$75k-$100k",
        },
        {
            "username": "robert_garcia",
            "email": "robert.garcia@auroramart.com",
            "first_name": "Robert",
            "last_name": "Garcia",
            "age": 41,
            "age_range": "35-44",
            "gender": "Male",
            "household_size": 5,
            "has_children": True,
            "occupation": "Skilled Trades",
            "education": "Diploma",
            "monthly_income": 62000,
            "employment": "Self-employed",
            "income_range": "$50k-$75k",
        },
        {
            "username": "amanda_white",
            "email": "amanda.white@auroramart.com",
            "first_name": "Amanda",
            "last_name": "White",
            "age": 35,
            "age_range": "35-44",
            "gender": "Female",
            "household_size": 3,
            "has_children": True,
            "occupation": "Admin",
            "education": "Bachelor",
            "monthly_income": 48000,
            "employment": "Full-time",
            "income_range": "$30k-$50k",
        },
    ]
    
    created_count = 0
    for user_data in sample_users:
        username = user_data.pop("username")
        email = user_data.pop("email")
        
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(
                username=username,
                email=email,
                password="demo123",  # Simple password for testing
                **user_data
            )
            created_count += 1
            print(f"  Created user: {username} ({user_data['age_range']}, {user_data['occupation']})")
        else:
            print(f"  User {username} already exists, skipping...")
    
    print(f"Created {created_count} sample users\n")
    return created_count


def main():
    parser = argparse.ArgumentParser(
        description="Seed a small catalog with images, prices, and stock."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing products/categories first.",
    )
    parser.add_argument(
        "--per-category",
        type=int,
        default=3,
        help="Products per subcategory.",
    )
    parser.add_argument(
        "--variants",
        type=int,
        default=3,
        help="Variants per product.",
    )
    args = parser.parse_args()
    seed(
        reset=args.reset,
        per_category=args.per_category,
        variants_per_product=args.variants,
    )


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)
    main()


