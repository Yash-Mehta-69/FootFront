from django.core.management.base import BaseCommand
from store.models import User, Category, Product, ProductVariant, Color, Size, Customer
from vendor.models import Vendor
from cart.models import Order, OrderItem, Shipment, ShippingAddress
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Populates the database with dummy vendor data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting dummy data population...')

        # 1. Create Vendor User
        email = 'vendor@footfront.com'
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(email=email, password='password', first_name='John', last_name='Vendor', role='vendor')
            vendor = Vendor.objects.create(
                user=user, 
                shopName='Kicks Palace', 
                shopAddress='123 Sneaker St, NYC', 
                business_phone='1234567890',
                description='The best place for premium sneakers.'
            )
            self.stdout.write(self.style.SUCCESS(f'Created vendor: {email}'))
        else:
            user = User.objects.get(email=email)
            vendor = user.vendor_profile
            self.stdout.write(self.style.SUCCESS(f'Using existing vendor: {email}'))

        # 2. Create Categories
        categories = ['Sneakers', 'Running', 'Casual', 'Basketball', 'Boots']
        cat_objs = []
        for cat_name in categories:
            cat, created = Category.objects.get_or_create(name=cat_name, defaults={'description': f'All about {cat_name}'})
            cat_objs.append(cat)
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(categories)} categories.'))

        # 3. Create Colors and Sizes
        colors = [('Red', '#FF0000'), ('Blue', '#0000FF'), ('Black', '#000000'), ('White', '#FFFFFF')]
        sizes = ['US 7', 'US 8', 'US 9', 'US 10', 'US 11']
        
        col_objs = []
        for name, hex_code in colors:
            c, _ = Color.objects.get_or_create(name=name, defaults={'hex_code': hex_code})
            col_objs.append(c)
            
        size_objs = []
        for label in sizes:
            s, _ = Size.objects.get_or_create(size_label=label)
            size_objs.append(s)

        # 4. Create Products
        product_names = ['Air Max 90', 'UltraBoost 21', 'Jordan 1 High', 'Classic Leather', 'Chuck Taylor']
        products = []
        for name in product_names:
            if not Product.objects.filter(name=name).exists():
                prod = Product.objects.create(
                    name=name,
                    description=f"This is a premium pair of {name}.",
                    vendor=vendor,
                    category=random.choice(cat_objs),
                    gender='U',
                    is_trending=random.choice([True, False])
                )
                products.append(prod)
                self.stdout.write(self.style.SUCCESS(f'Created product: {name}'))
            else:
                 products.append(Product.objects.get(name=name))

        # 5. Create Variants
        variants = []
        for product in products:
            for _ in range(3): # Create 3 variants per product
                variant = ProductVariant.objects.create(
                    product=product,
                    size=random.choice(size_objs),
                    color=random.choice(col_objs),
                    price=random.randint(80, 250),
                    stock=random.randint(10, 100),
                    image=None # Skipping image for dummy data
                )
                variants.append(variant)
        self.stdout.write(self.style.SUCCESS(f'Created {len(variants)} product variants.'))

        # 6. Create Customers
        customer_emails = ['alice@example.com', 'bob@example.com', 'charlie@example.com']
        customers = []
        for email in customer_emails:
            if not User.objects.filter(email=email).exists():
                u = User.objects.create_user(email=email, password='password', first_name=email.split('@')[0].capitalize(), last_name='User', role='user')
                cust = Customer.objects.create(user=u, phone=str(random.randint(1000000000, 9999999999)))
                customers.append(cust)
                
                # Create Shipping Address
                ShippingAddress.objects.create(
                    customer=cust,
                    address_line1=f"{random.randint(1,999)} Main St",
                    city='Metropolis',
                    state='NY',
                    postal_code='10001'
                )
            else:
                customers.append(Customer.objects.get(user__email=email))

        # 7. Create Orders, OrderItems and Shipments
        statuses = ['pending', 'shipped', 'delivered', 'cancelled']
        couriers = ['FedEx', 'UPS', 'DHL', 'USPS']

        for _ in range(10): # Create 10 orders
            customer = random.choice(customers)
            order = Order.objects.create(
                customer=customer,
                total_amount=0, # Will update
                shipping_address=ShippingAddress.objects.filter(customer=customer).first()
            )
            
            total = 0
            # Create 1-3 items per order
            for _ in range(random.randint(1, 3)):
                variant = random.choice(variants)
                quantity = random.randint(1, 2)
                price = variant.price
                item_total = price * quantity
                total += item_total
                
                order_item = OrderItem.objects.create(
                    order=order,
                    product_variant=variant,
                    quantity=quantity,
                    price=price
                )
                
                # Randomly create shipment for this item
                if random.choice([True, True, False]): # 66% chance of having shipment
                    status = random.choice(statuses)
                    shipped_at = timezone.now() - timedelta(days=random.randint(1, 10)) if status != 'pending' else timezone.now()
                    expected = shipped_at + timedelta(days=5)
                    
                    Shipment.objects.create(
                        order_item=order_item,
                        vendor=vendor,
                        tracking_number=f"TRK{random.randint(100000, 999999)}",
                        courier_name=random.choice(couriers),
                        status=status,
                        shipped_at=shipped_at,
                        expected_delivery=expected
                    )

            order.total_amount = total
            order.save()

        self.stdout.write(self.style.SUCCESS('Successfully populated dummy data!'))
