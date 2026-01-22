import os
import sys
import django
from django.utils.text import slugify

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FootFront.settings')
django.setup()

from store.models import Product, Category, Color, Size
from vendor.models import Vendor
from store.models import User

def test_unique_slugs():
    print("Testing unique slug generation...")
    
    # 1. Setup Dependencies
    try:
        user, _ = User.objects.get_or_create(email='test_slug_vendor@example.com', defaults={'role': 'vendor', 'first_name': 'Slug', 'last_name': 'Tester'})
        vendor, _ = Vendor.objects.get_or_create(user=user, defaults={'shopName': 'Slug Shop', 'business_phone': '1234567890'})
        category, _ = Category.objects.get_or_create(name='Slug Test Category', slug='slug-test-cat')
    except Exception as e:
        print(f"Setup Error: {e}")
        return

    product_name = "Unique Slug Test Product"
    expected_slug_base = slugify(product_name)
    
    # 2. Cleanup previous runs
    Product.objects.filter(name=product_name).delete()
    
    # 3. Create First Product
    print(f"Creating product 1: '{product_name}'")
    p1 = Product.objects.create(
        name=product_name,
        vendor=vendor,
        category=category,
        description="Test 1",

        # Product model fields: name, slug, description, vendor, category, gender, product_image, is_trending
    )
    print(f"   Product 1 Slug: {p1.slug}")
    if p1.slug == expected_slug_base:
        print("   PASS: First slug is correct.")
    else:
        print(f"   FAIL: Expected {expected_slug_base}, got {p1.slug}")

    # 4. Create Second Product (Same Name)
    print(f"Creating product 2: '{product_name}'")
    p2 = Product.objects.create(
        name=product_name,
        vendor=vendor,
        category=category,
        description="Test 2"
    )
    print(f"   Product 2 Slug: {p2.slug}")
    if p2.slug == f"{expected_slug_base}-1":
        print("   PASS: Second slug has -1 suffix.")
    else:
        print(f"   FAIL: Expected {expected_slug_base}-1, got {p2.slug}")

    # 5. Create Third Product (Same Name)
    print(f"Creating product 3: '{product_name}'")
    p3 = Product.objects.create(
        name=product_name,
        vendor=vendor,
        category=category,
        description="Test 3"
    )
    print(f"   Product 3 Slug: {p3.slug}")
    if p3.slug == f"{expected_slug_base}-2":
        print("   PASS: Third slug has -2 suffix.")
    else:
        print(f"   FAIL: Expected {expected_slug_base}-2, got {p3.slug}")

    # Cleanup
    p1.delete()
    p2.delete()
    p3.delete()
    
if __name__ == "__main__":
    test_unique_slugs()
