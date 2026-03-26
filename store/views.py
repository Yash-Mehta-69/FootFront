from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
import firebase_admin
from firebase_admin import credentials, auth
import mimetypes
from django.conf import settings
from .models import User, Customer, Category, Product, Color, Size
from .decorators import redirect_special_users
from django.db.models import Min, Q
from django.db import models
from django.contrib.auth.forms import PasswordResetForm
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
from .forms import ComplaintForm, UserUpdateForm, ShippingAddressForm
from .models import User, Customer, Category, Product, Color, Size, ShippingAddress, Review, ProductVariant, Complaint
from cart.models import Order
from utils.error_parser import parse_firebase_error



@redirect_special_users
def admin_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Unauthorized access attempt. Admin privileges required.')
        else:
            messages.error(request, 'Invalid administrator credentials.')
    return render(request, 'admin_login.html')


def vendor_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Ensure the user is a vendor
            if hasattr(user, 'vendor_profile'):
                vendor = user.vendor_profile
                
                # Security Checks
                if vendor.is_blocked:
                    messages.error(request, 'Your vendor account has been suspended. Please contact support.')
                elif vendor.is_deleted:
                    messages.error(request, 'Vendor identity not found in our records.')
                else:
                    login(request, user)
                    return redirect('vendor_dashboard')
            else:
                messages.error(request, 'Access denied. Account is not registered as a vendor.')
        else:
            messages.error(request, 'Authentication failed. Please check your Vendor ID and Access Key.')
    
    return render(request, 'vendor_login.html')

def password_reset_request(request, template_name, role_check):
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            print(f"DEBUG: Attempting password reset for email: {data} with role: {role_check}")
            
            # Broaden check for admin: role='admin' OR is_staff OR is_superuser
            if role_check == 'admin':
                associated_users = User.objects.filter(Q(email=data) & (Q(role='admin') | Q(is_staff=True) | Q(is_superuser=True)))
            else:
                associated_users = User.objects.filter(Q(email=data) & Q(role=role_check))

            if associated_users.exists():
                print(f"DEBUG: Found {associated_users.count()} user(s).")
                for user in associated_users:
                    print(f"DEBUG: Preparing email for user: {user.email}")
                    subject = "Password Reset Requested"
                    email_template_name = "password_reset_email.txt"
                    c = {
                        "email": user.email,
                        'domain': request.META['HTTP_HOST'],
                        'site_name': 'FootFront',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        'token': default_token_generator.make_token(user),
                        'protocol': 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    try:
                        send_mail(subject, email, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                        print("DEBUG: send_mail called successfully")
                    except Exception as e:
                         print(f"DEBUG: Error sending email: {e}")
                         messages.error(request, 'System error while transmitting reset link.')
                         return render(request, template_name, {"form": password_reset_form})
                
                messages.success(request, 'A message with reset instructions has been sent to your inbox.')
                return redirect(request.path)
            else:
                 print(f"DEBUG: No user found with email {data} and role {role_check}")
                 messages.error(request, f'This email is not registered as a {role_check}.')
        else:
            messages.error(request, 'Invalid email format.')
    else:
        password_reset_form = PasswordResetForm()
        
    return render(request, template_name, {"form": password_reset_form})

@redirect_special_users
def admin_forgot_password(request):
    return password_reset_request(request, 'admin_forgot_password.html', 'admin')

@redirect_special_users
def vendor_forgot_password(request):
    return password_reset_request(request, 'vendor_forgot_password.html', 'vendor')


def initialize_firebase():
    try:
        app = firebase_admin.get_app()
        print(f"DEBUG: Firebase already initialized for project: {app.project_id}")
    except ValueError:
        # Check for environment variable first
        firebase_config_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
        
        if firebase_config_json:
            import json
            cred_dict = json.loads(firebase_config_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # Fallback to file (will fail in production if file missing)
            cred = credentials.Certificate(settings.FIREBASE_ADMIN_CONFIG)
            
        app = firebase_admin.initialize_app(cred)
        print(f"DEBUG: Firebase initialized for project: {app.project_id}")

# Create your views here.
@redirect_special_users
def index(request):
    categories = Category.objects.filter(is_deleted=False)
    trending_products = Product.objects.filter(is_deleted=False, is_trending=True).annotate(price=Min('productvariant__price'))[:10]
    all_products = Product.objects.filter(is_deleted=False).annotate(price=Min('productvariant__price')).order_by('-created_at')[:10]
    
    # Homepage Reviews (Top rated, latest 5)
    featured_reviews = Review.objects.filter(is_deleted=False, rating__gte=4).order_by('-created_at')[:5]

    # Wishlist states
    wishlist_product_ids = []
    if request.user.is_authenticated:
        from cart.models import Wishlist
        wishlist_product_ids = list(Wishlist.objects.filter(
            customer=request.user.customer_profile,
            is_deleted=False
        ).values_list('product_variant__product_id', flat=True).distinct())

    context = {
        'categories': categories,
        'trending_products': trending_products,
        'all_products': all_products,
        'featured_reviews': featured_reviews,
        'wishlist_product_ids': wishlist_product_ids,
    }
    return render(request, 'index.html', context)

@csrf_exempt
@redirect_special_users
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        try:
            initialize_firebase()
            body = json.loads(request.body)
            id_token = body.get('idToken')
            
            if not id_token:
                return JsonResponse({'status': 'error', 'message': 'ID token is required.'}, status=400)

            # Verify the ID token with leeway for clock skew
            decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=60)
            uid = decoded_token['uid']
            email = decoded_token['email']

            # Authenticate based on role
            user = None
            if User.objects.filter(email=email).exists():
               user = User.objects.get(email=email)
               
               # Check Role Consistency
               if user.role == 'customer':
                   if hasattr(user, 'customer_profile'):
                       cust = user.customer_profile
                       if cust.is_blocked:
                           return JsonResponse({'status': 'error', 'message': 'Your account is suspended.'}, status=403)
                       if cust.is_deleted:
                           return JsonResponse({'status': 'error', 'message': 'Account deleted. Please register again.'}, status=403)
               elif user.role == 'vendor':
                   if hasattr(user, 'vendor_profile'):
                       vend = user.vendor_profile
                       if vend.is_blocked:
                           return JsonResponse({'status': 'error', 'message': 'Vendor account suspended. Contact Admin.'}, status=403)
                       if vend.is_deleted:
                            return JsonResponse({'status': 'error', 'message': 'Vendor account deleted.'}, status=403)
               
               login(request, user)
               return JsonResponse({'status': 'success', 'redirect_url': '/'})
            else:
                 # No user found with this email
                 return JsonResponse({'status': 'error', 'message': 'User not registered.'}, status=404)

        except Customer.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Account not found. Please register explicitly.'}, status=404)
        except auth.ExpiredIdTokenError:
            return JsonResponse({'status': 'error', 'message': 'Session expired. Please try logging in again.'}, status=401)
        except auth.RevokedIdTokenError:
            return JsonResponse({'status': 'error', 'message': 'Session revoked. Please login again.'}, status=401)
        except auth.InvalidIdTokenError as e:
            print(f"DEBUG: InvalidIdTokenError during login: {e}") # Log for admin
            print(f"DEBUG: Token starts with: {id_token[:10]}... ends with: {id_token[-10:] if id_token else 'None'}")
            return JsonResponse({'status': 'error', 'message': 'Authentication failed (Invalid Token). Please refresh and try again.'}, status=401)
        except Exception as e:
            print(f"DEBUG: Login Error: {e}") # Log full error
            return JsonResponse({'status': 'error', 'message': parse_firebase_error(e)}, status=500)
            
    return render(request, 'login.html')

@csrf_exempt
@redirect_special_users
def registration_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        try:
            initialize_firebase()
            body = json.loads(request.body)
            id_token = body.get('idToken')
            first_name = body.get('firstName')
            last_name = body.get('lastName', '')
            phone = body.get('phone')

            if not all([id_token, first_name, phone]):
                return JsonResponse({'status': 'error', 'message': 'First name and phone number are required.'}, status=400)

            # Debugging: Log token verification attempt
            # print(f"DEBUG: Verifying token for registration...") 
            
            try:
                decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=60)
            except Exception as token_error:
                print(f"DEBUG: Token Verification Failed: {token_error}")
                print(f"DEBUG: Token snippet: {id_token[:10]}...{id_token[-10:] if id_token else 'None'}")
                raise token_error # Re-raise to be caught below

            uid = decoded_token['uid']
            email = decoded_token.get('email')

            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                # Check for soft-deleted customer
                try:
                    customer = existing_user.customer_profile
                    if customer.is_deleted:
                        # Reactivate
                        customer.is_deleted = False
                        customer.firebase_uid = uid
                        customer.phone = phone # accurate phone from new reg
                        customer.is_blocked = False # Unblock on new registration if desired
                        customer.save()
                        
                        existing_user.first_name = first_name
                        existing_user.last_name = last_name
                        existing_user.save()
                        
                        login(request, existing_user)
                        return JsonResponse({'status': 'success', 'redirect_url': '/'})
                    else:
                        return JsonResponse({'status': 'error', 'message': 'A user with this email already exists.'}, status=409)
                except Customer.DoesNotExist:
                     # User exists but no customer profile?
                     return JsonResponse({'status': 'error', 'message': 'User profile inconsistency. Contact support.'}, status=500)
            
            if Customer.objects.filter(phone=phone).exists():
                 # Handle phone number reuse or conflict?
                 # If phone exists but not email, another user has it.
                 return JsonResponse({'status': 'error', 'message': 'This phone number is listed with another account.'}, status=409)

            if Customer.objects.filter(firebase_uid=uid).exists():
                 return JsonResponse({'status': 'error', 'message': 'Account already exists.'}, status=409)

            user = User.objects.create_user(email=email, first_name=first_name, last_name=last_name, role='customer')
            Customer.objects.create(user=user, phone=phone, firebase_uid=uid)
            login(request, user)

            return JsonResponse({'status': 'success', 'redirect_url': '/'})

        except auth.ExpiredIdTokenError:
            return JsonResponse({'status': 'error', 'message': 'Registration session expired. Please try again.'}, status=401)
        except auth.InvalidIdTokenError as e:
             print(f"DEBUG: InvalidIdTokenError during registration: {e}")
             return JsonResponse({'status': 'error', 'message': 'Invalid authentication token. Please refresh the page.'}, status=401)
        except Exception as e:
            print(f"DEBUG: Registration Error: {e}")
            return JsonResponse({'status': 'error', 'message': parse_firebase_error(e)}, status=500)

    return render(request, 'registration.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@csrf_exempt
def forgot_password_view(request):
    if request.method == 'POST':
        try:
            initialize_firebase()
            # Check if user is already logged in for API calls
            if request.user.is_authenticated:
                 return JsonResponse({'status': 'error', 'message': 'You are already logged in. Please logout to reset password.'}, status=403)

            body = json.loads(request.body)
            email = body.get('email')
            if not email:
                return JsonResponse({'status': 'error', 'message': 'Email is required.'}, status=400)
            if not User.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'This email is not registered in our system.'}, status=404)
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
             return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': parse_firebase_error(e)}, status=500)
    
    # GET Request
    if request.user.is_authenticated:
        return redirect('home')
        
    return render(request, 'forgot_password.html')

@login_required(login_url='login')
@redirect_special_users
def profile_view(request):
    try:
        customer = request.user.customer_profile
    except Customer.DoesNotExist:
        messages.error(request, "Customer profile not found.")
        return redirect('home')

    user_form = UserUpdateForm(instance=request.user, initial={'phone': customer.phone})

    # Order Statistics
    order_count = Order.objects.filter(customer=customer).count()

    # Tier Logic
    if order_count >= 50:
        tier_name = "LEGENDARY"
    elif order_count >= 20:
        tier_name = "ELITE"
    elif order_count >= 5:
        tier_name = "PRO"
    else:
        tier_name = "ROOKIE"

    context = {
        'user_form': user_form,
        'order_count': order_count,
        'tier_name': tier_name,
    }
    return render(request, 'profile.html', context)



@login_required(login_url='login')
@redirect_special_users
def profile_settings(request):
    try:
        customer = request.user.customer_profile
    except Customer.DoesNotExist:
        messages.error(request, "Customer profile not found.")
        return redirect('home')

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            # Update phone in Customer model
            new_phone = form.cleaned_data.get('phone')
            if new_phone:
                customer.phone = new_phone
                customer.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile_settings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserUpdateForm(instance=request.user, initial={'phone': customer.phone})

    context = {
        'user_form': form,
    }
    return render(request, 'profile_settings.html', context)

@login_required(login_url='login')
@redirect_special_users
def address_list(request):
    try:
        customer = request.user.customer_profile
    except Customer.DoesNotExist:
         messages.error(request, "Customer profile not found.")
         return redirect('home')
         
    addresses = ShippingAddress.objects.filter(customer=customer, is_deleted=False)
    return render(request, 'address_list.html', {'addresses': addresses})

@login_required(login_url='login')
@redirect_special_users
def address_add(request):
    try:
        customer = request.user.customer_profile
    except Customer.DoesNotExist:
         return redirect('home')

    if request.method == 'POST':
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.customer = customer
            address.save()
            messages.success(request, "Address added successfully.")
            return redirect('address_list')
    else:
        form = ShippingAddressForm()
    
    return render(request, 'address_form.html', {'form': form})

@login_required(login_url='login')
@redirect_special_users
def address_edit(request, address_id):
    try:
        customer = request.user.customer_profile
        address = ShippingAddress.objects.get(id=address_id, customer=customer, is_deleted=False)
    except (Customer.DoesNotExist, ShippingAddress.DoesNotExist):
        return redirect('address_list')

    if request.method == 'POST':
        form = ShippingAddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated successfully.")
            return redirect('address_list')
    else:
        form = ShippingAddressForm(instance=address)
    
    return render(request, 'address_form.html', {'form': form})

@login_required(login_url='login')
@redirect_special_users
def address_delete(request, address_id):
    try:
        customer = request.user.customer_profile
        address = ShippingAddress.objects.get(id=address_id, customer=customer, is_deleted=False)
        address.is_deleted = True # Soft delete
        address.save()
        messages.success(request, "Address deleted successfully.")
    except (Customer.DoesNotExist, ShippingAddress.DoesNotExist):
        pass
    return redirect('address_list')

from cart.models import Order, OrderItem

@login_required(login_url='login')
@redirect_special_users
def order_list(request):
    try:
        customer = request.user.customer_profile
    except Customer.DoesNotExist:
         return redirect('home')
         
    orders = Order.objects.filter(customer=customer, is_deleted=False).order_by('-order_date')
    return render(request, 'order_list.html', {'orders': orders})

@login_required(login_url='login')
@redirect_special_users
def my_complaints(request):
    try:
        customer = request.user.customer_profile
        user_complaints = Complaint.objects.filter(customer=customer, is_deleted=False).order_by('-created_at')
    except:
        user_complaints = []
        
    return render(request, 'my_complaints.html', {'user_complaints': user_complaints})

@login_required(login_url='login')
@redirect_special_users
def order_detail(request, order_id):
    try:
        customer = request.user.customer_profile
        order = Order.objects.get(id=order_id, customer=customer, is_deleted=False)
        items = order.items.filter(is_deleted=False)
    except (Customer.DoesNotExist, Order.DoesNotExist):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Order not found'}, status=404)
        return redirect('order_list')
        
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'includes/order_detail_partial.html', {'order': order, 'items': items})
        
    return render(request, 'order_detail.html', {'order': order, 'items': items})



from django.db.models import Min, Q

@redirect_special_users
def shop(request):
    products = Product.objects.filter(is_deleted=False).select_related('category')
    categories = Category.objects.filter(is_deleted=False)
    colors = Color.objects.all()
    sizes = Size.objects.all()
    
    # Annotate with minimum price (assuming product has variants)
    # We use 'productvariant__price' to access the price field in the related ProductVariant model
    products = products.annotate(price=Min('productvariant__price'))

    # --- Filtering ---
    # Category
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)
        
    # Search
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)

    # Price Range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Color
    color_name = request.GET.get('color')
    if color_name:
        products = products.filter(productvariant__color__name=color_name).distinct()

    # Size
    size_label = request.GET.get('size')
    if size_label:
        products = products.filter(productvariant__size__size_label=size_label).distinct()

    # Gender
    gender_code = request.GET.get('gender')
    if gender_code:
        products = products.filter(gender=gender_code)

    # --- Sorting ---
    sort_by = request.GET.get('sort')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:
        # Default sort
        products = products.order_by('-created_at')

    # --- Pagination ---
    from django.core.paginator import Paginator
    paginator = Paginator(products, 10) # 1 product per page as requested
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Wishlist states
    wishlist_product_ids = []
    if request.user.is_authenticated:
        from cart.models import Wishlist
        wishlist_product_ids = list(Wishlist.objects.filter(
            customer=request.user.customer_profile,
            is_deleted=False
        ).values_list('product_variant__product_id', flat=True).distinct())

    context = {
        'products': page_obj, 
        'categories': categories,
        'colors': colors,
        'sizes': sizes,
        'genders': Product.GENDER_CHOICES,
        'wishlist_product_ids': wishlist_product_ids,
    }
    return render(request, 'shop.html', context)

@redirect_special_users
def api_search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'products': []})
    
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_deleted=False
    ).select_related('category').annotate(min_price=Min('productvariant__price'))[:5]
    
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'price': float(product.min_price) if product.min_price else 0,
            'image': product.product_image.url if product.product_image else '/static/images/placeholder-shoe.png',
            'category': product.category.name if product.category else 'Sneakers',
            'url': f"/product/{product.slug}/"
        })
    
    return JsonResponse({'products': results})

from .forms import CustomerPasswordChangeForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

@login_required(login_url='login')
@redirect_special_users
def change_password(request):
    user = request.user
    is_customer = hasattr(user, 'customer_profile')
    
    if request.method == 'POST':
        if is_customer:
            # All users now see "Old Password" field via CustomerPasswordChangeForm
            form = CustomerPasswordChangeForm(user, request.POST)
        else:
            # Admins/Vendors use standard PasswordChangeForm
            form = PasswordChangeForm(user, request.POST)
            
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            
            if is_customer:
                customer = user.customer_profile
                if customer.firebase_uid:
                    try:
                        initialize_firebase()
                        # Update Firebase Password
                        auth.update_user(customer.firebase_uid, password=new_password)
                    except Exception as e:
                        print(f"DEBUG: Firebase Password Update Error: {e}")
                        messages.error(request, f"Identity provider synchronization failed: {parse_firebase_error(e)}")
                        return render(request, 'change_password.html', {'form': form})

            # Save Django password
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated across all protocols.')
            return redirect('profile_settings')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        if is_customer:
            form = CustomerPasswordChangeForm(user)
        else:
            form = PasswordChangeForm(user)
            
    # Add styles to form fields (Always apply, even on errors/re-render)
    for field in form.fields:
        form.fields[field].widget.attrs.update({
            'class': 'form-control',
            'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);' 
        })
            
    return render(request, 'change_password.html', {'form': form})

@login_required(login_url='login')
@redirect_special_users
def my_reviews(request):
    try:
        customer = request.user.customer_profile
        reviews = Review.objects.filter(customer=customer, is_deleted=False).order_by('-created_at')
    except Exception as e:
        print(f"DEBUG: Error fetching reviews: {e}")
        reviews = []
        
    return render(request, 'my_reviews.html', {'reviews': reviews})

@redirect_special_users
def product_detail(request, slug):
    try:
        product = Product.objects.annotate(price=Min('productvariant__price')).get(slug=slug, is_deleted=False)
        variants = product.productvariant_set.filter(is_deleted=False)
        
        # Get unique colors and sizes available for this product, filtering out None values safely
        colors = sorted([c for c in set(v.color for v in variants) if c], key=lambda c: c.name)
        sizes = sorted([s for s in set(v.size for v in variants) if s], key=lambda s: s.size_label)
        
        # Reviews
        reviews = Review.objects.filter(product=product, is_deleted=False).order_by('-created_at')
        avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0
        review_count = reviews.count()
        
        # Rating Breakdown
        rating_counts = {
            5: reviews.filter(rating=5).count(),
            4: reviews.filter(rating=4).count(),
            3: reviews.filter(rating=3).count(),
            2: reviews.filter(rating=2).count(),
            1: reviews.filter(rating=1).count(),
        }
        rating_percentages = {
            star: int((count / review_count) * 100) if review_count > 0 else 0
            for star, count in rating_counts.items()
        }
        # Cart and Wishlist states for variants
        in_cart_variant_ids = []
        in_cart_quantities = {} # New: Map variant_id -> quantity
        in_wishlist_variant_ids = []
        
        if request.user.is_authenticated:
            try:
                customer = request.user.customer_profile
                # Review Eligibility Logic
                from cart.models import CartItem, Wishlist, OrderItem, Shipment
                from django.utils import timezone
                from datetime import timedelta

                # 1. Check all order items for this product
                all_order_items = OrderItem.objects.filter(
                    order__customer=customer,
                    product_variant__product=product,
                    is_deleted=False
                ).select_related('shipment', 'order').order_by('-order__order_date')

                if not all_order_items.exists():
                    can_review = False
                    eligibility_message = "Only verified buyers who have received the product can leave a review."
                else:
                    # 2. Existing Review Check
                    if Review.objects.filter(customer=customer, product=product, is_deleted=False).exists():
                        can_review = False
                        eligibility_message = "You have already reviewed this product."
                    else:
                        # 3. Check latest order state and 30-day window
                        latest_item = all_order_items.first()
                        window_days = 30
                        eligible_with_window = False
                        has_undelivered = False

                        for item in all_order_items:
                            if hasattr(item, 'shipment') and item.shipment.status == 'delivered':
                                shipment = item.shipment
                                last_status = shipment.history.filter(status='delivered').first()
                                delivery_time = last_status.created_at if last_status else shipment.shipped_at
                                
                                if delivery_time and (timezone.now() - delivery_time) <= timedelta(days=window_days):
                                    eligible_with_window = True
                                    break
                                elif not delivery_time:
                                    eligible_with_window = True
                                    break
                            else:
                                has_undelivered = True
                        
                        if eligible_with_window:
                            can_review = True
                            eligibility_message = ""
                        elif has_undelivered:
                            can_review = False
                            eligibility_message = "Only verified buyers who have received the product can leave a review. Please wait for your recent order to be delivered."
                        else:
                            can_review = False
                            eligibility_message = f"The review window for this purchase has expired ({window_days} days post-delivery)."

                # Cart and Wishlist states for variants
                cart_items = CartItem.objects.filter(
                    cart__customer=customer, 
                    product_variant__product=product,
                    is_deleted=False
                )
                in_cart_variant_ids = list(cart_items.values_list('product_variant_id', flat=True))
                # Create map: {variant_id: quantity}
                for item in cart_items:
                    in_cart_quantities[item.product_variant_id] = item.quantity
                
                # Get variant IDs in wishlist
                in_wishlist_variant_ids = list(Wishlist.objects.filter(
                    customer=customer,
                    product_variant__product=product,
                    is_deleted=False
                ).values_list('product_variant_id', flat=True))
            except Exception as e:
                print(f"DEBUG: Error fetching review/cart/wishlist states: {e}")

    except Product.DoesNotExist:
        return redirect('shop')
            
    context = {
        'product': product,
        'variants': variants,
        'available_colors': colors,
        'available_sizes': sizes,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'review_count': review_count,
        'rating_percentages': rating_percentages,
        'rating_percentages': rating_percentages,
        'in_cart_variant_ids': in_cart_variant_ids,
        'in_cart_quantities': in_cart_quantities, # New context
        'in_wishlist_variant_ids': in_wishlist_variant_ids,
        'can_review': locals().get('can_review', False),
        'eligibility_message': locals().get('eligibility_message', "Login to leave a review."),
    }
    return render(request, 'product_detail.html', context)

from .forms import ReviewForm
from .models import ReviewMedia

@login_required(login_url='login')
@redirect_special_users
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        try:
            # Check if user has a customer profile
            try:
                customer = request.user.customer_profile
            except Customer.DoesNotExist:
                messages.error(request, 'Only customers can add reviews.')
                return redirect('product_detail', slug=product.slug)

            form = ReviewForm(request.POST, request.FILES)
            if form.is_valid():
                # --- Security Reinforcement: Re-verify Constraints ---
                from cart.models import OrderItem, Shipment
                from django.utils import timezone
                from datetime import timedelta

                # 1. Purchase & Delivery Check
                all_order_items = OrderItem.objects.filter(
                    order__customer=customer,
                    product_variant__product=product,
                    is_deleted=False
                ).select_related('shipment', 'order').order_by('-order__order_date')

                if not all_order_items.exists():
                    messages.error(request, "Only verified buyers who have received the product can leave a review.")
                    return redirect('product_detail', slug=product.slug)

                # 2. Existing Review Check
                if Review.objects.filter(customer=customer, product=product, is_deleted=False).exists():
                    messages.error(request, "You have already reviewed this product.")
                    return redirect('product_detail', slug=product.slug)

                # 3. Time Window Check (30 Days)
                window_days = 30
                eligible_with_window = False
                has_undelivered = False
                
                for item in all_order_items:
                    if hasattr(item, 'shipment') and item.shipment.status == 'delivered':
                        shipment = item.shipment
                        last_status = shipment.history.filter(status='delivered').first()
                        delivery_time = last_status.created_at if last_status else shipment.shipped_at
                        
                        if delivery_time and (timezone.now() - delivery_time) <= timedelta(days=window_days):
                            eligible_with_window = True
                            break
                        elif not delivery_time:
                            eligible_with_window = True
                            break
                    else:
                        has_undelivered = True
                
                if not eligible_with_window:
                    if has_undelivered:
                        messages.error(request, "Please wait for your recent order to be delivered before reviewing.")
                    else:
                        messages.error(request, f"The review window for this purchase has expired ({window_days} days post-delivery).")
                    return redirect('product_detail', slug=product.slug)
                # --- End Constraints ---

                review = form.save(commit=False)
                review.product = product
                review.customer = customer
                review.save()
                
                # Handle Media
                files = request.FILES.getlist('media')
                print(f"DEBUG: Processing {len(files)} files for review {review.id}")
                for f in files:
                    mime_type = f.content_type or ''
                    # Enhanced detection: Check MIME type AND extension
                    guessed_type, _ = mimetypes.guess_type(f.name)
                    
                    print(f"DEBUG: File: {f.name}, MIME: {mime_type}, Guessed: {guessed_type}, Size: {f.size}")

                    is_video = 'video' in mime_type
                    
                    if not is_video and guessed_type and 'video' in guessed_type:
                        is_video = True
                        print(f"DEBUG: {f.name} detected as video via extension.")
                        
                    media_type = 'video' if is_video else 'image'
                    print(f"DEBUG: Saving {f.name} as {media_type}")
                    ReviewMedia.objects.create(review=review, file=f, media_type=media_type)
                    
                messages.success(request, 'Review submitted successfully!')
            else:
                 print(f"DEBUG: Review form errors: {form.errors}")
                 messages.error(request, 'Error submitting review. Please check the form.')
        except Exception as e:
             print(f"DEBUG: Exception in add_review: {e}")
             messages.error(request, f"An error occurred: {e}")
             
    return redirect('product_detail', slug=product.slug)

@redirect_special_users
def complaint_view(request):
    # Dummy Company Details
    company_details = {
        'address': 'ST.Xaviers College Ahmedabad Gujarat 380006',
        'email': 'support@footfront.com',
        'phone': '+91 98765 43210',
        'hours': 'Mon - Fri, 9am - 6pm PST'
    }

    # Dummy FAQs
    faqs = [
        {
            'question': 'How do I track my order?',
            'answer': 'You can track your order by logging into your account and visiting the "Orders" section. You will also receive an email with a tracking link once your order ships.'
        },
        {
            'question': 'Are the sneakers authentic?',
            'answer': 'Absolutely. Every pair on FootFront is verified by our expert team of authenticators before being shipped to you.'
        },
        {
            'question': 'How can I change my shipping address?',
            'answer': 'If your order hasn\'t shipped yet, please contact support immediately. Once shipped, we cannot change the destination.'
        },
        {
            'question': 'What payment methods do you accept?',
            'answer': 'We accept all major payment methods including credit cards, UPI, and  NetBanking.'
        }
    ]

    form = ComplaintForm()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to submit a complaint.")
            return redirect('login')
             
        # Check if user has a customer profile
        try:
            customer = request.user.customer_profile
        except Customer.DoesNotExist:
             messages.error(request, "Customer profile not found.")
             return redirect('home')

        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.customer = customer
            complaint.status = 'Pending'
            complaint.save()
            messages.success(request, "Your ticket has been submitted successfully! We will contact you shortly.")
            return redirect('complaint') # Redirect back to complaint page instead of help which might not exist
        else:
            messages.error(request, "Please correct the errors below.")

    context = {
        'company_details': company_details,
        'faqs': faqs,
        'form': form,
    }
    return render(request, 'complaint.html', context)

@login_required(login_url='login')
@redirect_special_users
def my_complaints(request):
    try:
        customer = request.user.customer_profile
        user_complaints = Complaint.objects.filter(customer=customer, is_deleted=False).order_by('-created_at')
    except:
        user_complaints = []
        
    return render(request, 'my_complaints.html', {'user_complaints': user_complaints})



@redirect_special_users
def terms_view(request):
    return render(request, 'terms.html')

@redirect_special_users
def privacy_view(request):
    return render(request, 'privacy.html')

@redirect_special_users
def contact_view(request):
    if request.method == 'POST':
        messages.success(request, "Thanks for reaching out! We'll get back to you shortly.")
        return redirect('contact')
    return render(request, 'contact.html')

@redirect_special_users
def cookie_policy_view(request):
    return render(request, 'cookie_policy.html')


@redirect_special_users
def become_vendor(request):
    return render(request, 'become_vendor.html')

from vendor.models import Vendor
@redirect_special_users
def vendor_shop(request):
    vendor_id = request.GET.get('id')
    try:
        vendor = Vendor.objects.get(pk=vendor_id, is_deleted=False, is_blocked=False)
    except (Vendor.DoesNotExist, ValueError):
        return redirect('shop')
        
    products = Product.objects.filter(vendor=vendor, is_deleted=False).select_related('category')
    
    # Calculate Real Stats
    from django.db.models import Avg, Sum
    products_count = products.count()
    
    # Real Avg Rating: Average of all reviews for all products of this vendor
    rating_avg_data = Review.objects.filter(product__vendor=vendor, is_deleted=False).aggregate(Avg('rating'))
    rating_avg = round(rating_avg_data['rating__avg'] or 4.9, 1) # Default to 4.9 for display if no reviews
    
    # Real Sold Count: Sum of quantities in OrderItems for all products of this vendor
    sold_count_data = OrderItem.objects.filter(product_variant__product__vendor=vendor, is_deleted=False).aggregate(Sum('quantity'))
    sold_count = sold_count_data['quantity__sum'] or 0
    
    # Filtering/Sorting Logic (Reuse from shop view)
    from django.db.models import Min
    products = products.annotate(price=Min('productvariant__price'))
    
    # Sort
    sort_by = request.GET.get('sort')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    else: # Default: Newest
        products = products.order_by('-created_at')
    # Pagination
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(products, 5) # Show 2 products per page to force pagination visibility
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    # Mask vendor details for customer
    masked_phone = vendor.business_phone
    if masked_phone and len(masked_phone) >= 4:
        masked_phone = '*' * (len(masked_phone) - 4) + masked_phone[-4:]

    masked_email = vendor.user.email if vendor.user and vendor.user.email else ''
    if masked_email and '@' in masked_email:
        name_part, domain_part = masked_email.split('@', 1)
        if len(name_part) > 2:
            name_part = name_part[:2] + '*' * (len(name_part) - 2)
        else:
            name_part = '*' * len(name_part)
        masked_email = f"{name_part}@{domain_part}"

    masked_address = vendor.shopAddress
    if masked_address:
        parts = masked_address.split(',')
        if len(parts) > 1:
            first_part = parts[0]
            masked_address = '*' * len(first_part) + ',' + ','.join(parts[1:])
        else:
            half = len(masked_address) // 2
            masked_address = '*' * half + masked_address[half:]

    context = {
        'vendor': vendor,
        'products': products,
        'products_count': products_count,
        'sold_count': sold_count,
        'rating_avg': rating_avg,
        'masked_phone': masked_phone,
        'masked_email': masked_email,
        'masked_address': masked_address,
    }
    return render(request, 'vendor_shop.html', context)

@redirect_special_users
def toggle_wishlist(request):
    import json
    from django.http import JsonResponse
    from cart.models import Wishlist
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'login_required'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            variant_id = data.get('variant_id')
            product_id = data.get('product_id')
            
            customer = request.user.customer_profile
            variant = None
            
            if variant_id:
                variant = get_object_or_404(ProductVariant, id=variant_id)
            elif product_id:
                product = get_object_or_404(Product, id=product_id)
                # Check if any variant of this product is already in wishlist
                existing_wishlist = Wishlist.objects.filter(customer=customer, product_variant__product=product, is_deleted=False)
                
                if existing_wishlist.exists():
                    # If we toggle from product card and it exists, remove ALL variants to clear it
                    count = existing_wishlist.count()
                    existing_wishlist.delete()
                    return JsonResponse({'success': True, 'action': 'removed', 'message': f'Removed {count} variants of {product.name}'})
                else:
                    # Otherwise, add the first available variant
                    variant = product.productvariant_set.filter(is_deleted=False).first()
                    if not variant:
                        return JsonResponse({'success': False, 'message': 'No variants available.'})
            else:
                return JsonResponse({'success': False, 'message': 'Target missing.'})

            wishlist_item, created = Wishlist.objects.get_or_create(
                customer=customer,
                product_variant=variant,
                is_deleted=False
            )
            
            variant_name = f"{variant.product.name} ({variant.color.name} / {variant.size.size_label})"
            
            if not created:
                wishlist_item.delete()
                action = 'removed'
            else:
                action = 'added'
                
            return JsonResponse({
                'success': True, 
                'action': action, 
                'variant_name': variant_name
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
            
    return JsonResponse({'success': False, 'message': 'Invalid request method'})




from utils.pdf_generator import render_to_pdf

@login_required(login_url='login')
def download_invoice(request, order_id):
    user = request.user
    
    # 1. Fetch Order
    try:
        if user.role == 'admin' or user.is_staff or user.is_superuser:
             order = Order.objects.select_related('customer', 'shipping_address', 'payment', 'customer__user').get(pk=order_id, is_deleted=False)
        elif user.role == 'vendor':
             # Vendor can only see orders that contain their products
             if not hasattr(user, 'vendor_profile'):
                 messages.error(request, "Vendor profile not found.")
                 return redirect('vendor_dashboard')
                 
             vendor = user.vendor_profile
             # Verify if this order has items from this vendor
             has_items = OrderItem.objects.filter(order_id=order_id, product_variant__product__vendor=vendor).exists()
             if not has_items:
                  messages.error(request, "Unauthorized access to this order.")
                  return redirect('vendor_orders')
             
             order = Order.objects.select_related('customer', 'shipping_address', 'payment', 'customer__user').get(pk=order_id, is_deleted=False)
        else:
             # Customer
             customer = user.customer_profile
             order = Order.objects.select_related('customer', 'shipping_address', 'payment', 'customer__user').get(pk=order_id, customer=customer, is_deleted=False)
             
    except (Order.DoesNotExist, Customer.DoesNotExist):
        messages.error(request, "Order not found or unauthorized.")
        # Try to redirect to home or some safe place
        return redirect('home')

    # 2. Fetch Items
    # For Vendor, we might want to show ONLY their items or ALL items? 
    # Usually an invoice is for the whole order for the Customer. 
    # For Vendor, they might want a packing slip, but the request says "Invoice".
    # If it's a platform invoice, it should show everything.
    # Let's assume the full invoice is generated for everyone for now, as it's "Download Invoice".
    items = order.items.filter(is_deleted=False).select_related('product_variant', 'product_variant__product', 'product_variant__color', 'product_variant__size')

    # 3. Context
    context = {
        'order': order,
        'items': items,
    }
    
    # 4. Render PDF
    pdf = render_to_pdf('utils/invoice.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Invoice_{order.id}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
    
    return HttpResponse("Not Found")
