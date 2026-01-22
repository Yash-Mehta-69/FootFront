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



@redirect_special_users
def admin_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('admin_dashboard')
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
                    return render(request, 'vendor_login.html')
                
                if vendor.is_deleted:
                    messages.error(request, 'Vendor account not found.')
                    return render(request, 'vendor_login.html')

                login(request, user)
                return redirect('vendordashboard')
            else:
                messages.error(request, 'You are not authorized as a vendor.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'vendor_login.html')

def password_reset_request(request, template_name, role_check):
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            print(f"DEBUG: Attempting password reset for email: {data} with role: {role_check}")
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
                        print("DEBUG: Calling send_mail...")
                        send_mail(subject, email, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                        print("DEBUG: send_mail called successfully")
                    except BadHeaderError:
                        print("DEBUG: BadHeaderError")
                        return HttpResponse('Invalid header found.')
                    except Exception as e:
                         print(f"DEBUG: Error sending email: {e}")
                
                messages.success(request, 'A message with reset instructions has been sent to your inbox.')
                return redirect(request.path)
            else:
                 print(f"DEBUG: No user found with email {data} and role {role_check}")
                 messages.error(request, 'This email is not registered as a ' + role_check + '.')
    return render(request, template_name)

@redirect_special_users
def admin_forgot_password(request):
    return password_reset_request(request, 'admin_forgot_password.html', 'admin')

@redirect_special_users
def vendor_forgot_password(request):
    return password_reset_request(request, 'vendor_forgot_password.html', 'vendor')


def initialize_firebase():
    try:
        firebase_admin.get_app()
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
            
        firebase_admin.initialize_app(cred)

# Create your views here.
@redirect_special_users
@redirect_special_users
def index(request):
    categories = Category.objects.filter(is_deleted=False)
    trending_products = Product.objects.filter(is_deleted=False, is_trending=True).annotate(price=Min('productvariant__price'))[:10]
    all_products = Product.objects.filter(is_deleted=False).annotate(price=Min('productvariant__price')).order_by('-created_at')[:10]
    
    # Homepage Reviews (Top rated, latest 5)
    featured_reviews = Review.objects.filter(is_deleted=False, rating__gte=4).order_by('-created_at')[:5]

    context = {
        'categories': categories,
        'trending_products': trending_products,
        'all_products': all_products,
        'featured_reviews': featured_reviews,
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

            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token)
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
        except auth.InvalidIdTokenError:
            print(f"DEBUG: InvalidIdTokenError during login.") # Log for admin
            return JsonResponse({'status': 'error', 'message': 'Authentication failed (Invalid Token). Please refresh and try again.'}, status=401)
        except Exception as e:
            print(f"DEBUG: Login Error: {e}") # Log full error
            return JsonResponse({'status': 'error', 'message': "An system error occurred during login. Please contact support."}, status=500)
            
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
                decoded_token = auth.verify_id_token(id_token)
            except Exception as token_error:
                print(f"DEBUG: Token Verification Failed: {token_error}")
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

            user = User.objects.create_user(email=email, first_name=first_name, last_name=last_name, role='user')
            Customer.objects.create(user=user, phone=phone, firebase_uid=uid)
            login(request, user)

            return JsonResponse({'status': 'success', 'redirect_url': '/'})

        except auth.ExpiredIdTokenError:
            return JsonResponse({'status': 'error', 'message': 'Registration session expired. Please try again.'}, status=401)
        except auth.InvalidIdTokenError:
             print(f"DEBUG: InvalidIdTokenError during registration.")
             return JsonResponse({'status': 'error', 'message': 'Invalid authentication token. Please refresh the page.'}, status=401)
        except Exception as e:
            print(f"DEBUG: Registration Error: {e}")
            return JsonResponse({'status': 'error', 'message': "Registration failed due to a system error."}, status=500)

    return render(request, 'registration.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@csrf_exempt
@redirect_special_users
def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            email = body.get('email')
            if not email:
                return JsonResponse({'status': 'error', 'message': 'Email is required.'}, status=400)
            if not User.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'This email is not registered in our system.'}, status=404)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
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
def address_list(request):
    try:
        customer = request.user.customer_profile
    except Customer.DoesNotExist:
         messages.error(request, "Customer profile not found.")
         return redirect('home')
         
    addresses = ShippingAddress.objects.filter(customer=customer, is_deleted=False)
    return render(request, 'address_list.html', {'addresses': addresses})

@login_required(login_url='login')
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
def order_list(request):
    try:
        customer = request.user.customer_profile
    except Customer.DoesNotExist:
         return redirect('home')
         
    orders = Order.objects.filter(customer=customer, is_deleted=False).order_by('-order_date')
    return render(request, 'order_list.html', {'orders': orders})

@login_required(login_url='login')
def order_detail(request, order_id):
    # Handle Demo IDs for the popup
    if str(order_id) in ["001234", "001235", "1234", "1235", "123", "000123"]:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # For demo, we just pass the ID, the template handles static demo content
            return render(request, 'includes/order_detail_partial.html', {
                'order': {'id': str(order_id).zfill(6), 'total_amount': '438.50'}
            })
        return redirect('order_list')

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

    context = {
        'products': page_obj, # This is now the page object, but template can iterate it same way
        'categories': categories,
        'colors': colors,
        'sizes': sizes,
        'genders': Product.GENDER_CHOICES,
    }
    return render(request, 'shop.html', context)

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

from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile_settings')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
        # Add styles to form fields
        for field in form.fields:
            form.fields[field].widget.attrs.update({
                'class': 'form-control',
                'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);' 
            })
            
    return render(request, 'change_password.html', {'form': form})

@login_required(login_url='login')
def my_reviews(request):
    # Fetch real reviews if any
    try:
        customer = request.user.customer_profile
        reviews = Review.objects.filter(customer=customer, is_deleted=False).order_by('-created_at')
    except:
        reviews = []
        
    return render(request, 'my_reviews.html', {'reviews': reviews})

def product_detail(request, slug):
    try:
        product = Product.objects.annotate(price=Min('productvariant__price')).get(slug=slug, is_deleted=False)
        variants = product.productvariant_set.filter(is_deleted=False)
        
        # Get unique colors and sizes available for this product
        colors = sorted(list(set(v.color for v in variants)), key=lambda c: c.name)
        sizes = sorted(list(set(v.size for v in variants)), key=lambda s: s.size_label)
        
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
    }
    return render(request, 'product_detail.html', context)

from .forms import ReviewForm
from .models import ReviewMedia

@login_required(login_url='login')
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

            # Check if user already reviewed
            existing_review = Review.objects.filter(product=product, customer=customer, is_deleted=False).first()
            if existing_review:
                messages.error(request, 'You have already reviewed this product.')
                return redirect('product_detail', slug=product.slug)

            form = ReviewForm(request.POST, request.FILES)
            if form.is_valid():
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

def complaint_view(request):
    # Dummy Company Details
    company_details = {
        'address': '123 Tech Avenue, Innovation City, CA 90210',
        'email': 'support@footfront.com',
        'phone': '+1 (555) 019-2834',
        'hours': 'Mon - Fri, 9am - 6pm PST'
    }

    # Dummy FAQs
    faqs = [
        {
            'question': 'How do I track my order?',
            'answer': 'You can track your order by logging into your account and visiting the "Orders" section. You will also receive an email with a tracking link once your order ships.'
        },
        {
            'question': 'What is your return policy?',
            'answer': 'We offer a 30-day return policy for unmatched items. Shoes must be unworn and in original packaging. Visit our Returns page to start a return.'
        },
        {
            'question': 'Do you ship internationally?',
            'answer': 'Yes! We ship to over 50 countries worldwide. Shipping rates and times vary by location and are calculated at checkout.'
        },
        {
            'question': 'Are the sneakers authentic?',
            'answer': 'Absolutely. Every pair on FootFront is verified by our expert team of authenticators before being shipped to you.'
        },
         {
            'question': 'How can I change my shipping address?',
            'answer': 'If your order hasn\'t shipped yet, please contact support immediately. Once shipped, we cannot change the destination.'
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
            complaint.save()
            messages.success(request, "Your ticket has been submitted successfully! We will contact you shortly.")
            return redirect('help')
        else:
            messages.error(request, "Please correct the errors below.")

    # Fetch User's Complaints
    user_complaints = []
    if request.user.is_authenticated:
        try:
            customer = request.user.customer_profile
            user_complaints = Complaint.objects.filter(customer=customer, is_deleted=False).order_by('-created_at')
        except:
            pass

    context = {
        'company_details': company_details,
        'faqs': faqs,
        'form': form,
        'user_complaints': user_complaints
    }
    return render(request, 'complaint.html', context)



def terms_view(request):
    return render(request, 'terms.html')

def privacy_view(request):
    return render(request, 'privacy.html')

def contact_view(request):
    if request.method == 'POST':
        messages.success(request, "Thanks for reaching out! We'll get back to you shortly.")
        return redirect('contact')
    return render(request, 'contact.html')

def cookie_policy_view(request):
    return render(request, 'cookie_policy.html')


def become_vendor(request):
    return render(request, 'become_vendor.html')

from vendor.models import Vendor
def vendor_shop(request):
    vendor_id = request.GET.get('id')
    try:
        vendor = Vendor.objects.get(pk=vendor_id, is_deleted=False, is_blocked=False)
    except (Vendor.DoesNotExist, ValueError):
        return redirect('shop')
        
    products = Product.objects.filter(vendor=vendor, is_deleted=False).select_related('category')
    
    # Calculate Stats
    products_count = products.count()
    # Mock data for now, real orders require complex aggregation
    sold_count = 120 # Placeholder or aggregate OrderItems
    rating_avg = 4.9 # Placeholder or aggregate Reviews
    
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

    context = {
        'vendor': vendor,
        'products': products,
        'products_count': products_count,
        'sold_count': sold_count,
        'rating_avg': rating_avg,
    }
    return render(request, 'vendor_shop.html', context)

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
            variant = get_object_or_404(ProductVariant, id=variant_id)
            customer = request.user.customer_profile
            
            wishlist_item, created = Wishlist.objects.get_or_create(
                customer=customer,
                product_variant=variant
            )
            
            if not created:
                # If it already exists, remove it (toggle)
                wishlist_item.delete()
                action = 'removed'
            else:
                action = 'added'
                
            return JsonResponse({'success': True, 'action': action})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
            
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


