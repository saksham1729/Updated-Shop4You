from django.shortcuts import render, redirect, HttpResponse, redirect
from .models import Customer, Product, Cart, OrderPlaced
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

from app.models import ProductRating
from datetime import timedelta
from django.utils import timezone

from django.conf import settings

import traceback
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from app.models import Product, ProductRating
from threading import Thread
import subprocess

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import OrderPlaced
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import escape
import google.generativeai as genai

from django.conf import settings

from app.models import RecommendationLog
from django.http import JsonResponse
from recommend_engine.recommend import recommend_products
from app.models import ProductRating, Product, OrderPlaced


import random
from django.shortcuts import render, redirect
from django.contrib import messages
from twilio.rest import Client
from .forms import CustomerDetailsForm, CustomerProfileForm, ProfileImageForm
from .forms import PhoneForm, OTPVerificationForm



import os

model_path = os.path.join(settings.BASE_DIR, 'recommend_engine', 'model.pkl')
columns_path = os.path.join(settings.BASE_DIR, 'recommend_engine', 'columns.pkl')


def log_product_click(user, product_id):
		RecommendationLog.objects.create(
			user=user,
			product_id=product_id,
			source="product_clicked"
		) 

from recommend_engine.recommend import recommend_products

class ProductView(View):
	def get(self, request):
		totalitem = 0
		recommendations = []
		if request.user.is_authenticated:
			totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
			recommendations = recommend_products(
				user_id=request.user.id,
				model_path='recommend_engine/random_forest.pkl',
				columns_path='recommend_engine/input_columns.pkl'
			)

		# Existing categories
		topwears = Product.objects.filter(category='TW')
		bottomwears = Product.objects.filter(category='BW')
		mobiles = Product.objects.filter(category='M')
		laptops = Product.objects.filter(category='L')
		cables = Product.objects.filter(category='C')
		television = Product.objects.filter(category='TV')


		return render(request, 'app/home.html', {
			'topwears': topwears,
			'bottomwears': bottomwears,
			'mobiles': mobiles,
			'laptops': laptops,
			'totalitem': totalitem,
			'cables': cables,
			'television': television,
			'recommendations': recommendations
		})

class ProductDetailView(View):
	def get(self, request, pk):
		totalitem = 0
		product = Product.objects.get(pk=pk)
		print(product.id)
		item_already_in_cart=False
		
		if request.user.is_authenticated:
				log_product_click(request.user, product.id)
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
	STATUS_FLOW = ['Pending','Accepted', 'Packed', 'On Way','Out for Delivery', 'Delivered', 'Cancelled']
	STEPS_WITH_LABELS = [
		('Pending', 'Pending'),
		('Accepted', 'Order Accepted'),
		('Packed', 'Packed'),
		('On Way','On Way'),
		('Out for Delivery','Out for Delivery'),
		('Delivered', 'Delivered'),
		('Cancelled', 'Cancelled')
	]

	order_placed = OrderPlaced.objects.filter(user=request.user).order_by('-ordered_date')
	user_address = request.user.customer_set.first()
	user_lat, user_lng = get_coordinates(f"{user_address.locality}, {user_address.city}, {user_address.state}")

	# Defensive fallback
	if None in (user_lat, user_lng):
		user_lat, user_lng = 25.3176, 82.9739  # Default to Varanasi or whatever you prefer

	

	for order in order_placed:
		order.delivery_info = order.get_delivery_estimate()


	for order in order_placed:
		current_index = STATUS_FLOW.index(order.status) if order.status in STATUS_FLOW else 0
		order.status_sequence = STATUS_FLOW[:current_index]
		
		product_location = order.product.location or "Delhi, India"
		warehouse_lat, warehouse_lng = get_coordinates(product_location)


		if None in (warehouse_lat, warehouse_lng):
			warehouse_lat, warehouse_lng = 28.6139, 77.2090  # Default to Delhi

		# ETA calculation

		if None not in (user_lat, user_lng, warehouse_lat, warehouse_lng):
			distance_km = haversine(user_lat, user_lng, warehouse_lat, warehouse_lng)
			avg_speed_kmph = 40
			eta_minutes = int(distance_km / avg_speed_kmph)  # Base buffer

	# Add extra time based on order status
			if order.status == "Pending":
				eta_minutes += 7000
			elif order.status == "Accepted":
				eta_minutes += 6600  # 6600 seconds → 110 minutes
			elif order.status == "Packed":
				eta_minutes += 5000   # 5000 seconds → ~83 minutes
			elif order.status == "On Way":
				eta_minutes +=4400  # 4400 seconds → ~73 minutes
			elif order.status == "Out for Delivery":
				eta_minutes += 200   # 4400 seconds → ~73 minutes
			elif order.status == "Delivered":
				order.eta = order.updated_at  # Timestamp of status update
			elif order.status == "Cancelled":
				order.eta = None
			else:
				order.eta = timezone.now() + timedelta(minutes=eta_minutes)  # Default

	# Save ETA only if not Delivered
			if order.status != "Delivered":
				order.eta = timezone.now() + timedelta(minutes=eta_minutes)
				order.save(update_fields=['eta'])
			else:
				order.save(update_fields=['eta'])

		else:
			order.eta = None

	reviewed = ProductRating.objects.filter(user=request.user)
	user_reviews = {
		r.product.id: {
			'rating': r.rating,
			'review': r.review
		} for r in reviewed
	}

	return render(request, 'app/orders.html', {
		'order_placed': order_placed,
		'user_reviews': user_reviews,
		'steps_with_labels': STEPS_WITH_LABELS
	})


	

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

def cables(request, data=None):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	
	if data is None:
		cables = Product.objects.filter(category='C')
	else:
		cables = Product.objects.filter(category='C')  # fallback

	return render(request, 'app/cables.html', {'cables': cables, 'totalitem': totalitem})

def television(request, data=None):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	
	if data is None:
		television = Product.objects.filter(category='TV')
	else:
		television = Product.objects.filter(category='TV')  # fallback

	return render(request, 'app/tv.html', {'television': television, 'totalitem': totalitem})

def office(request, data=None):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	
	if data is None:
		office = Product.objects.filter(category='OP')
	else:
		office = Product.objects.filter(category='OP')  # fallback

	return render(request, 'app/OfficeProducts.html', {'office': office, 'totalitem': totalitem})

def kitchen(request, data=None):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	
	if data is None:
		kitchen	 = Product.objects.filter(category='HK')
	else:
		kitchen = Product.objects.filter(category='HK')  # fallback

	return render(request, 'app/Home&Kitchen.html', {'kitchen': kitchen, 'totalitem': totalitem})

def waterheater(request, data=None):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	
	if data is None:
		waterheater	 = Product.objects.filter(category='WH')
	else:
		waterheater = Product.objects.filter(category='WH')  # fallback

	return render(request, 'app/WaterHeater.html', {'waterheater': waterheater, 'totalitem': totalitem})

def grinder(request, data=None):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	
	if data is None:
		grinder	 = Product.objects.filter(category='GD')
	else:
		grinder = Product.objects.filter(category='GD')  # fallback

	return render(request, 'app/Grinder&Blender.html', {'grinder': grinder, 'totalitem': totalitem})

def iron(request, data=None):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	
	if data is None:
		iron	 = Product.objects.filter(category='I')
	else:
		iron = Product.objects.filter(category='I')  # fallback

	return render(request, 'app/Iron.html', {'iron': iron, 'totalitem': totalitem})

def fans(request, data=None):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	
	if data is None:
		fans = Product.objects.filter(category='FAN')
	else:
		fans = Product.objects.filter(category='FAN')  # fallback

	return render(request, 'app/fans.html', {'fans': fans, 'totalitem': totalitem})

def roomheater(request, data=None):
	totalitem = 0
	if request.user.is_authenticated:
		totalitem = Cart.objects.filter(user=request.user).aggregate(Sum('quantity'))['quantity__sum'] or 0
	
	if data is None:
		roomheater	 = Product.objects.filter(category='RH')
	else:
		roomheater = Product.objects.filter(category='RH')  # fallback

	return render(request, 'app/RoomHeater.html', {'roomheater': roomheater, 'totalitem': totalitem})


class CustomerRegistrationView(View):
    def get(self, request):
        return render(request, 'app/customerregistration.html', {
            'phone_form': PhoneForm(),
            'otp_form': OTPVerificationForm(),
            'details_form': CustomerDetailsForm(),
        })

    def post(self, request):
        stage = request.POST.get('stage')

        if stage == 'send_otp':
            phone_form = PhoneForm(request.POST)
            if phone_form.is_valid():
                phone = phone_form.cleaned_data['phone']
                otp = str(random.randint(100000, 999999))

                # Send SMS using Twilio
                account_sid = 'AC51e24b5efcbfab0d198a7a46e0c815db'
                auth_token = 'f7965ec9fc79c5d77c046a3b25db4e18'
                client = Client(account_sid, auth_token)
                client.messages.create(
                    body=f"Your OTP is {otp}",
                    from_='+12176694297',
                    to='+91' + phone
                )

                request.session['phone'] = phone
                request.session['otp'] = otp

                messages.info(request, f"OTP sent to {phone}.")
                return render(request, 'app/customerregistration.html', {
                    'phone_form': phone_form,
                    'otp_form': OTPVerificationForm(),
                    'details_form': None,
                    'stage': 'otp'
                })

        elif stage == 'verify_otp':
            otp_form = OTPVerificationForm(request.POST)
            original_otp = request.session.get('otp')
            if otp_form.is_valid():
                if otp_form.cleaned_data['otp'] == original_otp:
                    messages.success(request, "OTP verified. Please complete your registration.")
                    return render(request, 'app/customerregistration.html', {
                        'phone_form': None,
                        'otp_form': None,
                        'details_form': CustomerDetailsForm(),
                        'stage': 'details'
                    })
                else:
                    messages.error(request, "Incorrect OTP.")
            return render(request, 'app/customerregistration.html', {
                'phone_form': None,
                'otp_form': otp_form,
                'details_form': None,
                'stage': 'otp'
            })

        elif stage == 'submit_details':
            details_form = CustomerDetailsForm(request.POST)
            if details_form.is_valid():
                user = details_form.save()
                phone = request.session.get('phone')

                # Save phone to related model if needed
                #Customer.objects.create(user=user, phone=phone)

                # Clear session
                request.session.flush()

                messages.success(request, "Registered successfully.")
                return redirect('login')

            return render(request, 'app/customerregistration.html', {
                'details_form': details_form,
                'stage': 'details'
            })


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
                return None, None  # Address not found
        except GeocoderUnavailable:
            time.sleep(delay)  # wait before retrying

    # All retries exhausted or geocoder unavailable throughout
    return 25.3176, 82.9739  # Default fallback coordinates



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


	
	
	# 🎯 Product recommendations
	if any(kw in query for kw in ['recommend', 'suggest', 'interested in', 'what should i buy', 'based on my taste']):
		if not user:
			return JsonResponse({'response': '🛡️ Please log in so I can tailor recommendations for you.'})

		model_path = 'recommend_engine/random_forest.pkl'
		columns_path = 'recommend_engine/input_columns.pkl'

		try:
			recommendations = recommend_products(user.id, model_path, columns_path)

			if not recommendations:
				return JsonResponse({'response': '🧠 I need a few product ratings first — once you rate some, I’ll have awesome picks ready!'})

		# 🔥 Enhanced product styling with image and price
			styled = ""
			for product in recommendations:
	# Determine image source: uploaded > external link > default
				if product.product_image and hasattr(product.product_image, 'url'):
					image_url = product.product_image.url
				elif hasattr(product, 'img_link') and product.img_link:
					image_url = product.img_link
				else:
					image_url = "/static/app/images/default.png"

				styled += (
					f"<div style='margin-bottom:10px;'>"
					f"<img src='{image_url}' width='100' style='border-radius:8px;' alt='{product.title}'><br>"
					f"<strong>{product.title}</strong><br>"
					f"💸 ₹{product.discounted_price}<br>"
					f"</div><hr>"
				)


			response_text = f"<div>🎯 Based on your style, here are some picks:<br><br>{styled}</div>"
			return JsonResponse({'response': response_text})

		except Exception as e:
				return JsonResponse({
					'response': "⚠️ Couldn't generate suggestions right now. Try again later.<br>" + str(e)
		})


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





def recommend_view(request, user_id):
	model_path = 'recommend_engine/random_forest.pkl'
	columns_path = 'recommend_engine/input_columns.pkl'

	try:
		recommendations = recommend_products(
			user_id=request.user.id,
			model_path=model_path,
			columns_path=columns_path  # ✅ This is the missing part
		)



		if not recommendations:
			return JsonResponse({
				"message": "No personalized suggestions yet. Try rating a few products!"
			})

		return JsonResponse({
			"message": f"Based on your preferences, here are some picks: {', '.join(recommendations)}"
		})

	except Exception as e:
		return JsonResponse({
			"error": str(e),
			"message": "Oops! Something went wrong while generating recommendations."
		})





# Background retraining
def trigger_model_retrain():
	def run():
		subprocess.call(['python', 'recommend_engine/model_train.py'])
	Thread(target=run).start()

@login_required
def submit_rating(request, product_id):
	if request.method == "POST":
		rating_value = float(request.POST.get("rating"))
		product = get_object_or_404(Product, id=product_id)
		user_reviews = request.POST.get('review').strip()  # or from a form


		# Update or create rating
		rating_obj, created = ProductRating.objects.update_or_create(
			user=request.user,
			product=product,
			defaults={'rating': rating_value , "review" : user_reviews }
		)

		# 💡 Trigger model retraining
		trigger_model_retrain()

		# Redirect to product page or thank-you page
		return redirect("orders")


from django.shortcuts import render
from recommend_engine.recommend import recommend_products
from app.models import RecommendationLog 

def recommend_view(request, user_id):
	recommended_products = recommend_products(
		user_id=user_id,
		model_path='recommend_engine/random_forest.pkl',
		columns_path='recommend_engine/input_columns.pkl'
	)

	# 📦 Log each recommendation served to the user
	for product in recommended_products:
		RecommendationLog.objects.create(
			user=request.user,
			product=product,
			source="recommend_view"  # optional: helps identify where the recommendation came from
		)

	message = ""
	if ProductRating.objects.filter(user_id=user_id).count() == 0:
		message = "Here's a curated list to get you started!"

	return render(request, 'app/recommend.html', {
		'recommended_products': recommended_products,
		'message': message
	})
