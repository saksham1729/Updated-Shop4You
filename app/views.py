from django.shortcuts import render, redirect, HttpResponse, redirect
from .models import Customer, Product, Cart, OrderPlaced
from .forms import CustomerRegistrationForm, CustomerProfileForm,  ProfileImageForm
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Sum
from django.conf import settings
import stripe
import math
from django.conf import settings
from geopy.geocoders import Nominatim
from .models import OrderPlaced
from geopy.distance import geodesic
from django.utils.safestring import mark_safe
import json
import time
from geopy.exc import GeocoderUnavailable

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import OrderPlaced
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import escape
import google.generativeai as genai
from django.conf import settings

class ProductView(View):
	def get(self, request):
		totalitem = 0
		topwears = Product.objects.filter(category='TW')
		bottomwears = Product.objects.filter(category='BW')
		mobiles = Product.objects.filter(category='M')
		laptops = Product.objects.filter(category='L')
		if request.user.is_authenticated:
			totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
		return render(request, 'app/home.html', {'topwears':topwears, 'bottomwears':bottomwears, 'mobiles':mobiles, 'laptops': laptops, 'totalitem':totalitem})

class ProductDetailView(View):
	def get(self, request, pk):
		totalitem = 0
		product = Product.objects.get(pk=pk)
		print(product.id)
		item_already_in_cart=False
		if request.user.is_authenticated:
			totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
			item_already_in_cart = Cart.objects.filter(Q(product=product.id) & Q(user=request.user)).exists()
		return render(request, 'app/productdetail.html', {'product':product, 'item_already_in_cart':item_already_in_cart, 'totalitem':totalitem})

@login_required()
def add_to_cart(request):
    user = request.user
    product_id = request.GET.get('prod_id')

    try:
        # Get the Product object
        product = Product.objects.get(id=product_id)

        # Check if item already exists in cart
        cart_item, created = Cart.objects.get_or_create(user=user, product=product)

        if not created:
            # If it already exists, increase quantity
            cart_item.quantity += 1
            cart_item.save()
            messages.info(request, 'Product quantity updated in cart!')
        else:
            # If new, it’s already saved with quantity = 1
            messages.success(request, 'Product added to cart successfully!')

    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')

    return redirect('/cart')


@login_required
def show_cart(request):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
		user = request.user
		cart = Cart.objects.filter(user=user)
		amount = 0.0
		shipping_amount = 70.0
		totalamount=0.0
		cart_product = [p for p in Cart.objects.all() if p.user == request.user]
		print(cart_product)
		if cart_product:
			for p in cart_product:
				tempamount = (p.quantity * p.product.discounted_price)
				amount += tempamount
				totalamount = amount+shipping_amount
			return render(request, 'app/addtocart.html', {'carts':cart, 'amount':amount, 'totalamount':totalamount, 'totalitem':totalitem})
		else:
			return render(request, 'app/emptycart.html', {'carts':cart, 'totalitem':totalitem})
	else:
		return render(request, 'app/emptycart.html', {'totalitem':totalitem})

@login_required
def plus_cart(request):
    if request.method == 'GET':
        prod_id = request.GET['prod_id']
        try:
            prod_id = request.GET.get('prod_id')
            c = Cart.objects.get(Q(product=prod_id) & Q(user=request.user))
            c.quantity += 1
            c.save()
            quantity = c.quantity

            amount = 0.0
            shipping_amount = 70.0

            cart_product = Cart.objects.filter(user=request.user)
            for p in cart_product:
                amount += p.quantity * p.product.discounted_price

            
            totalitem = cart_product.aggregate(Sum('quantity'))['quantity__sum'] or 0

            data = {
                'quantity': c.quantity,
                'amount': amount,
                'totalamount': amount + shipping_amount,
                'totalitem': totalitem
            }
            return JsonResponse(data)

        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Cart item not found'}, status=404)

    return HttpResponse("")



@login_required
def minus_cart(request):
    if request.method == 'GET':
        prod_id = request.GET.get('prod_id')
        try:
            c = Cart.objects.get(Q(product=prod_id) & Q(user=request.user))
            if c.quantity > 1:
                c.quantity -= 1
                c.save()
            else:
                c.delete()  # Optional: delete item if quantity goes to 0
        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Item not found in cart'}, status=404)

        amount = 0.0
        shipping_amount = 70.0
        cart_product = Cart.objects.filter(user=request.user)

        for p in cart_product:
            amount += p.quantity * p.product.discounted_price

        totalitem = cart_product.aggregate(Sum('quantity'))['quantity__sum'] or 0

        data = {
            'quantity': c.quantity if c.id else 0,
            'amount': amount,
            'totalamount': amount + shipping_amount,
            'totalitem': totalitem
        }
        return JsonResponse(data)
    else:
        return HttpResponse("Invalid request", status=400)


@login_required
def checkout(request):
    user = request.user
    add = Customer.objects.filter(user=user)
    cart_items = Cart.objects.filter(user=request.user)
    
    # FIX: Don't leave it with a trailing comma (it becomes a tuple)
    stripe_publishable_key = settings.STRIPE_PUBLIC_KEY
    
    return render(request, 'app/checkout.html', {
        'add': add,
        'cart_items': cart_items,
        'stripe_publishable_key': stripe_publishable_key
    })

@login_required
def payment_done(request):
	custid = request.GET.get('custid')
	print("Customer ID", custid)
	user = request.user
	cartid = Cart.objects.filter(user = user)
	customer = Customer.objects.get(id=custid)
	print(customer)
	for cid in cartid:
		OrderPlaced.objects.create(user=user, customer=customer, product=cid.product, quantity=cid.quantity).save()
		print("Order Saved")
		cid.delete()
		print("Cart Item Deleted")
	return redirect("orders")

def remove_cart(request):
    if request.method == 'GET':
        prod_id = request.GET['prod_id']
        try:
            c = Cart.objects.get(Q(product=prod_id) & Q(user=request.user))
            c.delete()
        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Cart item not found'}, status=404)

        amount = 0.0
        shipping_amount = 70.0
        cart_product = Cart.objects.filter(user=request.user)
        for p in cart_product:
            amount += p.quantity * p.product.discounted_price

        data = {
            'amount': amount,
            'totalamount': amount + shipping_amount
        }
        return JsonResponse(data)



@login_required
def address(request):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	add = Customer.objects.filter(user=request.user)
	return render(request, 'app/address.html', {'add':add, 'active':'btn-primary', 'totalitem':totalitem})

@login_required
def orders(request):
    order_placed = OrderPlaced.objects.filter(user=request.user).order_by('-ordered_date')
    return render(request, 'app/orders.html', {'order_placed': order_placed})
    

    

def mobile(request, data=None):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	if data==None :
			mobiles = Product.objects.filter(category='M')
	elif data == 'Redmi' or data == 'Samsung':
			mobiles = Product.objects.filter(category='M').filter(brand=data)
	elif data == 'below':
			mobiles = Product.objects.filter(category='M').filter(discounted_price__lt=10000)
	elif data == 'above':
			mobiles = Product.objects.filter(category='M').filter(discounted_price__gt=10000)
	return render(request, 'app/mobile.html', {'mobiles':mobiles, 'totalitem':totalitem})

def topwear(request, data=None):
    totalitem = 0
    if request.user.is_authenticated:
        totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    if data is None:
        topwears = Product.objects.filter(category='TW')
    elif data == 'Nike' or data == 'Adidas':  # Add your actual brand names here
        topwears = Product.objects.filter(category='TW', brand=data)
    elif data == 'below':
        topwears = Product.objects.filter(category='TW', discounted_price__lt=1000)
    elif data == 'above':
        topwears = Product.objects.filter(category='TW', discounted_price__gt=1000)
    else:
        topwears = Product.objects.filter(category='TW')  # fallback

    return render(request, 'app/top_wear.html', {'topwears': topwears, 'totalitem': totalitem})

def bottomwear(request, data=None):
    totalitem = 0
    if request.user.is_authenticated:
        totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    if data is None:
        bottomwears = Product.objects.filter(category='BW')  # Assuming 'BW' is the category code for Bottom Wear
    elif data in ['Levis', 'PepeJeans']:  # Add other brands here if needed
        bottomwears = Product.objects.filter(category='BW', brand=data)
    elif data == 'below':
        bottomwears = Product.objects.filter(category='BW', discounted_price__lt=1000)
    elif data == 'above':
        bottomwears = Product.objects.filter(category='BW', discounted_price__gt=1000)
    else:
        bottomwears = Product.objects.filter(category='BW')  # fallback for unexpected data

    return render(request, 'app/bottom_wear.html', {'bottomwears': bottomwears, 'totalitem': totalitem})


def laptop(request, data=None):
    totalitem = 0
    if request.user.is_authenticated:
        totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    if data is None:
        laptops = Product.objects.filter(category='L')
    elif data == 'Asus' or data == 'Acer' or data == 'Lenovo':  # Add your actual brand names here
        laptops = Product.objects.filter(category='L', brand=data)
    elif data == 'below':
        laptops = Product.objects.filter(category='L', discounted_price__lt=50000)
    elif data == 'above':
        laptops = Product.objects.filter(category='L', discounted_price__gt=50000)
    else:
        laptops = Product.objects.filter(category='L')  # fallback

    return render(request, 'app/laptop.html', {'laptops': laptops, 'totalitem': totalitem})


class CustomerRegistrationView(View):
 def get(self, request):
  form = CustomerRegistrationForm()
  return render(request, 'app/customerregistration.html', {'form':form})
  
 def post(self, request):
  form = CustomerRegistrationForm(request.POST)
  if form.is_valid():
        form.save()
        messages.success(request, 'Congratulations!! Registered Successfully.')
        return redirect('login')
  return render(request, 'app/customerregistration.html', {'form':form})

@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    def get(self, request):
        user_profile = request.user.profile  # Assumes Profile instance exists
        customer_form = CustomerProfileForm()
        profile_form = ProfileImageForm(instance=user_profile)
        return render(request, 'app/profile.html', {
            'form': customer_form,
            'profile_form': profile_form,
            'active': 'btn-primary'
        })

    def post(self, request):
        user_profile = request.user.profile
        customer_form = CustomerProfileForm(request.POST)
        profile_form = ProfileImageForm(request.POST, request.FILES, instance=user_profile)

        if customer_form.is_valid() and profile_form.is_valid():
            # Save customer data
            cd = customer_form.cleaned_data
            Customer.objects.create(
                user=request.user,
                name=cd['name'],
                locality=cd['locality'],
                city=cd['city'],
                state=cd['state'],
                zipcode=cd['zipcode']
            )


            # Save profile picture
            profile_form.save()

            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')

        return render(request, 'app/profile.html', {
            'form': customer_form,
            'profile_form': profile_form,
            'active': 'btn-primary'
        })
    

#for payments


# This is your test secret API key.

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def create_checkout_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cust_id = data.get('custid')
            user = request.user

            # Get cart items
            cart_items = Cart.objects.filter(user=user)
            if not cart_items.exists():
                return JsonResponse({'error': 'Cart is empty'}, status=400)

            # Total cost
            total_amount = sum(item.total_cost for item in cart_items)

            # Create Stripe session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'inr',
                        'unit_amount': int(total_amount * 100),  # amount in paise
                        'product_data': {
                            'name': 'Shop4You Order',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri('/payment-success/'),
                cancel_url=request.build_absolute_uri('/payment-cancel/'),
            )

            return JsonResponse({'id': session.id})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)
    
@login_required
def paymentSuccess(request):
    # You can also verify session ID from request.GET.get('session_id') if needed
    user = request.user
    cart_items = Cart.objects.filter(user=user)
    customer = Customer.objects.filter(user=user).last()

    for item in cart_items:
        order = OrderPlaced.objects.create(
            user=user,
            customer=customer,
            product=item.product,
            quantity=item.quantity
        )
        send_order_confirmation_email(user, order)
        item.delete()

    return render(request, 'app/success.html', {"payment_status": "success"})


@login_required
def paymentCancel(request):
    return render(request, 'app/cancel.html', {"payment_status": "cancel"})





def search_products(request):
    if request.method == "GET":
        query = request.GET.get('term', '')
        results = []
        if query:
            products = Product.objects.filter(title__icontains=query)[:5]
            for product in products:
                results.append({
                    'id': product.id,
                    'title': product.title,
                    'image': product.product_image.url,
                    'price': product.discounted_price,
                })
        return JsonResponse({'results': results})
    


geolocator = Nominatim(user_agent="shop4you", timeout=5)



def get_coordinates(address, retries=3, delay=1):
    for attempt in range(retries):
        try:
            location = geolocator.geocode(address)
            if location:
                return location.latitude, location.longitude
            else:
                return None, None
        except GeocoderUnavailable:
            time.sleep(delay)  # wait before retrying
    return None, None


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Radius of Earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c



def track_order(request, order_id):
    order = OrderPlaced.objects.get(id=order_id, user=request.user)
    user_address = request.user.customer_set.first()
    user_full_address = f"{user_address.locality}, {user_address.city}, {user_address.state}"
    user_lat, user_lng = get_coordinates(user_full_address)

    # 🔴 Fallback for user's coordinates
    if user_lat is None or user_lng is None:
        user_lat, user_lng = 25.3176, 82.9739  # Example: Varanasi fallback

    product_location = order.product.location or "Delhi, India"
    warehouse_lat, warehouse_lng = get_coordinates(product_location)

    # 🔴 Fallback for warehouse coordinates
    if warehouse_lat is None or warehouse_lng is None:
        warehouse_lat, warehouse_lng = 28.6139, 77.2090  # Example: Delhi fallback


    # Calculate distance and ETA
    distance_km = haversine(user_lat, user_lng, warehouse_lat, warehouse_lng)
    avg_speed_kmph = 40
    eta_minutes = int((distance_km / avg_speed_kmph))

    product_data = [{
        'title': order.product.title,
        'status': order.status,
        'lat': warehouse_lat,
        'lng': warehouse_lng,
        'eta': eta_minutes,
    }]

    context = {
        'user_lat': user_lat,
        'user_lng': user_lng,
        'products': mark_safe(json.dumps(product_data)),
        'eta'     : eta_minutes,
    }

    return render(request, 'app/track_order.html', context)


def send_order_confirmation_email(user, order):
    subject = 'Order Confirmation - Shop4You'
    message = f'Hi {user.first_name},\n\nYour order #{order.id} for {order.product.title} has been successfully placed!\n\nThank you for shopping with us!\n\n- Shop4You Team'
    recipient_list = [user.email]
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)


@csrf_exempt
def chatbot_query(request):
    query = request.GET.get('q', '').strip().lower()
    user = request.user if request.user.is_authenticated else None

    # 🧾 View recent orders
    if any(kw in query for kw in ['my orders', 'purchase', 'recent orders', 'order']):
        if not user:
            return JsonResponse({'response': '🛡️ Please log in to view your orders.'})

        orders = OrderPlaced.objects.filter(user=user).order_by('-ordered_date')[:3]
        if orders:
            response = "🧾 Here are your latest orders:<br>"
            for order in orders:
                response += (
                    f"<strong>{order.product.title}</strong> × {order.quantity}<br>"
                    f"📅 Ordered on: {order.ordered_date.strftime('%d %b %Y')}<br>"
                    f"<br>{order.status}<br><hr>"
                )
        else:
            response = "📭 You haven’t placed any orders yet."
        return JsonResponse({'response': response})

    # 🛒 View cart items
    if any(kw in query for kw in ['cart', 'my cart', 'items in cart', 'shopping']):
        if not user:
            return JsonResponse({'response': '🛡️ Please log in to view your cart.'})

        cart_items = Cart.objects.filter(user=user)
        if cart_items.exists():
            response = "🛒 Items in your cart:<br><br>"
            
            for item in cart_items:
                response += (
                    f"{item.product.title} × {item.quantity}<br>"
                    f"💸 ₹{item.product.discounted_price} each<br><hr>"
                )
        else:
            response = "🛍️ Your cart is currently empty."
        return JsonResponse({'response': response})

    # 🧠 Product search fallback
    product = Product.objects.filter(title__icontains=query).first()
    if product:
        response_text = (
            f"<strong>{escape(product.title)}</strong><br>"
            f"💸 Price: ₹{product.discounted_price}<br>"
            f"📝 Description: {escape(product.description)}"
        )
    else:
        # 🌐 Fallback to Gemini AI if product/cart/order not found
        response_text = get_gemini_response(query)

    return JsonResponse({'response': response_text})


genai.configure(api_key=settings.GENAI_API_KEY)

def get_gemini_response(prompt):
    if not prompt:
        return "⚠️ Please enter a valid query."

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content([{"text": prompt}])

        if hasattr(response, 'text') and response.text:
            return response.text.strip()
        else:
            return "🤖 Gemini didn't return a response. Try rephrasing your question."
    except Exception as e:
        print("Gemini API error:", str(e))  # Log for debugging
        return "⚠️ Gemini couldn't process your request right now. Try again later."

import traceback
print("Gemini API error:", traceback.format_exc())
