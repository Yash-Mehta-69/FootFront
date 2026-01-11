from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings
from .models import User, Customer, Category, Product, Color, Size
from .decorators import redirect_special_users
from django.db.models import Min, Q



def admin_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/admin/')
    return render(request, 'admin_login.html')


def vendor_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(f"Attempting login for vendor username: {username}"
              f" and password: {password}")
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Ensure the user is a vendor
            if hasattr(user, 'vendor_profile'):  # Check if the user has a vendor profile
                login(request, user)
                
                print(request, 'Login successful!')
               
                return redirect('vendordashboard')  # Redirect to vendor dashboard
            else:
                print(request, 'You are not authorized as a vendor.')
        else:
            print(request, 'Invalid username or password.')
    
    return render(request, 'vendor_login.html')


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
def index(request):
    categories = Category.objects.filter(is_deleted=False)
    trending_products = Product.objects.filter(is_deleted=False, is_trending=True)[:8]
    all_products = Product.objects.filter(is_deleted=False).order_by('?')[:12] # Random mix for "All Products"
    context = {
        'categories': categories,
        'trending_products': trending_products,
        'all_products': all_products
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

            # Get the customer profile using firebase_uid, then get the user
            customer = Customer.objects.get(firebase_uid=uid)
            user = customer.user
            login(request, user)
            
            return JsonResponse({'status': 'success', 'redirect_url': '/'})

        except Customer.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found in our database. Please register first.'}, status=404)
        except auth.InvalidIdTokenError:
            return JsonResponse({'status': 'error', 'message': 'Invalid ID token.'}, status=401)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
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

            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token['uid']
            email = decoded_token.get('email')

            if User.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'A user with this email already exists.'}, status=409)
            
            if Customer.objects.filter(phone=phone).exists() or Customer.objects.filter(firebase_uid=uid).exists():
                return JsonResponse({'status': 'error', 'message': 'This phone number or account is already in use.'}, status=409)

            user = User.objects.create_user(email=email, first_name=first_name, last_name=last_name, role='user')
            Customer.objects.create(user=user, phone=phone, firebase_uid=uid)
            login(request, user)

            return JsonResponse({'status': 'success', 'redirect_url': '/'})

        except auth.InvalidIdTokenError:
            return JsonResponse({'status': 'error', 'message': 'Invalid ID token.'}, status=401)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

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
    return render(request, 'profile.html')

from django.db.models import Min, Q

def shop(request):
    products = Product.objects.filter(is_deleted=False)
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
    paginator = Paginator(products, 1) # 1 product per page as requested
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

def product_detail(request):
    product_id = request.GET.get('id')
    product = None
    if product_id:
        try:
            product = Product.objects.annotate(price=Min('productvariant__price')).get(id=product_id, is_deleted=False)
        except Product.DoesNotExist:
            return redirect('shop')
            
    context = {
        'product': product,
    }
    return render(request, 'product_detail.html', context)
