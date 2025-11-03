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

RNG = random.Random(42)

# Use royalty‑free images (Unsplash/Pexels)
CATEGORIES = [
    (
        "Electronics",
        ["Phones", "Laptops"],
        [
            "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9",
            "https://images.unsplash.com/photo-1517336714731-489689fd1ca8",
            "https://images.unsplash.com/photo-1518779578993-ec3579fee39f",
        ],
    ),
    (
        "Fashion",
        ["Men", "Women"],
        [
            "https://images.unsplash.com/photo-1520975922325-24bc3f3b8f49",
            "https://images.unsplash.com/photo-1520975940462-3b3b3c25f6a0",
            "https://images.unsplash.com/photo-1520975661595-645b0f49b9c1",
        ],
    ),
    (
        "Home & Garden",
        ["Kitchen", "Furniture"],
        [
            "https://images.unsplash.com/photo-1505691938895-1758d7feb511",
            "https://images.unsplash.com/photo-1493666438817-866a91353ca9",
            "https://images.unsplash.com/photo-1497366811353-6870744d04b2",
        ],
    ),
    (
        "Sports",
        ["Fitness"],
        [
            "https://images.unsplash.com/photo-1517836357463-d25dfeac3438",
            "https://images.unsplash.com/photo-1526401281623-3599d94d2a32",
            "https://images.unsplash.com/photo-1518611012118-696072aa579a",
        ],
    ),
]


def base_price_for(category_name: str) -> tuple[int, int]:
    ranges = {
        "Electronics": (199, 1299),
        "Fashion": (15, 150),
        "Home & Garden": (10, 300),
        "Sports": (12, 250),
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


def ensure_product_image(product: Product, image_urls: list) -> ProductImage:
    img = product.images.order_by("order").first()
    if img:
        return img
    url = RNG.choice(image_urls)
    img = ProductImage(
        product=product,
        is_primary=True,
        order=0,
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


def product_defaults(name: str, cat: Category, idx: int) -> dict:
    base_slug = slugify(name)
    slug = unique_value(Product, "slug", base_slug)
    base_sku = f"{cat.name[:3].upper()}-{idx:04d}"
    sku = unique_value(Product, "sku", base_sku)
    return {
        "name": name,
        "slug": slug,
        "sku": sku,
        "category": cat,
        "description": f"High‑quality {name} with modern design and reliable performance.",
        "size_guide": "Refer to the product details for sizing.",
        "rating": Decimal(str(round(RNG.uniform(3.8, 5.0), 1))),
        "review_count": RNG.randint(3, 120),
        "is_trending": (idx % 5 == 0),
        "is_bestseller": (idx % 4 == 0),
        "is_featured": (idx % 3 == 0),
        "is_active": True,
    }


@transaction.atomic
def seed(reset: bool = False, per_category: int = 3, variants_per_product: int = 2):
    if reset:
        print("Resetting catalog…")
        ProductVariant.objects.all().delete()
        ProductImage.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()

    for top, subs, image_urls in CATEGORIES:
        parent, _ = Category.objects.get_or_create(
            name=top, defaults={"slug": slugify(top), "parent": None}
        )
        targets = []
        if subs:
            for s in subs:
                c, _ = Category.objects.get_or_create(
                    name=s, defaults={"slug": slugify(s), "parent": parent}
                )
                targets.append(c)
        else:
            targets = [parent]

        low, high = base_price_for(parent.name)

        for cat in targets:
            for i in range(1, per_category + 1):
                name = f"{cat.name} Product {i}"
                defaults = product_defaults(name, cat, i)

                # Use slug for lookup so re‑runs don’t duplicate by name
                product, created = Product.objects.get_or_create(
                    slug=defaults["slug"], defaults=defaults
                )
                if created:
                    print(f"Created product: {product.name}")
                else:
                    # Ensure required fields if product already existed
                    if not product.sku:
                        product.sku = unique_value(
                            Product, "sku", f"{cat.name[:3].upper()}-{i:04d}"
                        )
                    if not product.category_id:
                        product.category = cat
                    product.save()

                primary_img = ensure_product_image(product, image_urls)

                # Create a few variants with price/stock
                if product.variants.count() == 0:
                    for v in range(variants_per_product):
                        base_price = Decimal(RNG.randint(low, high))
                        price = max(
                            base_price + Decimal(RNG.randint(-20, 40)), Decimal("5.00")
                        )
                        compare = price + Decimal(RNG.choice([0, 10, 20, 50, 100]))
                        sku_suffix = chr(ord("A") + v)
                        ProductVariant.objects.create(
                            product=product,
                            sku=f"{product.sku}-{sku_suffix}",
                            price=price,
                            compare_price=compare if compare > price else None,
                            stock=RNG.randint(0, 80),
                            main_image=primary_img,
                            is_active=True,
                        )

    print(
        f"\nDone. Categories: {Category.objects.count()}, Products: {Product.objects.count()}, Variants: {ProductVariant.objects.count()}"
    )


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
        default=2,
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


