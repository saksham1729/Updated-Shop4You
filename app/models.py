from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta, date
from django.core.validators import MaxValueValidator, MinValueValidator
STATE_CHOICES = (
  ('Andaman & Nicobar Islands','Andaman & Nicobar Islands'),
  ('Andhra Pradesh','Andhra Pradesh'),
  ('Arunachal Pradesh','Arunachal Pradesh'),
  ('Assam','Assam'),
  ('Bihar','Bihar'),
  ('Chandigarh','Chandigarh'),
  ('Chhattisgarh','Chhattisgarh'),
  ('Dadra & Nagar Haveli','Dadra & Nagar Haveli'),
  ('Daman and Diu','Daman and Diu'),
  ('Delhi','Delhi'),
  ('Goa','Goa'),
  ('Gujarat','Gujarat'),
  ('Haryana','Haryana'),
  ('Himachal Pradesh','Himachal Pradesh'),
  ('Jammu & Kashmir','Jammu & Kashmir'),
  ('Jharkhand','Jharkhand'),
  ('Karnataka','Karnataka'),
  ('Kerala','Kerala'),
  ('Lakshadweep','Lakshadweep'),
  ('Madhya Pradesh','Madhya Pradesh'),
  ('Maharashtra','Maharashtra'),
  ('Manipur','Manipur'),
  ('Meghalaya','Meghalaya'),
  ('Mizoram','Mizoram'),
  ('Nagaland','Nagaland'),
  ('Odisha','Odisha'),
  ('Puducherry','Puducherry'),
  ('Punjab','Punjab'),
  ('Rajasthan','Rajasthan'),
  ('Sikkim','Sikkim'),
  ('Tamil Nadu','Tamil Nadu'),
  ('Telangana','Telangana'),
  ('Tripura','Tripura'),
  ('Uttarakhand','Uttarakhand'),
  ('Uttar Pradesh','Uttar Pradesh'),
  ('West Bengal','West Bengal'),
)
class Customer(models.Model):
 user = models.ForeignKey(User, on_delete=models.CASCADE)
 name = models.CharField(max_length=200)
 locality = models.CharField(max_length=200)
 city = models.CharField(max_length=50)
 zipcode = models.IntegerField(blank=True, null=True)
 state = models.CharField(choices=STATE_CHOICES, max_length=50)
 phone = models.CharField(max_length=15, blank=True)


 def __str__(self):
  # return self.user.username
  return str(self.id)


CATEGORY_CHOICES = (
 ('M', 'Mobile'),
 ('L', 'Laptop'),
 ('TW', 'Top Wear'),
 ('BW', 'Bottom Wear'),
 ('TV', 'Television'),
 ('C', 'Cables'),
 ('HK', 'Home & Kitchen'),
 ('OP', 'Office Products'),
 ('WH', 'Water Heaters'),
('I', 'Iron'),
('FAN', 'Fans'),
('GD', 'Grinder'),
('RH', 'Room Heaters'),
)
class Product(models.Model):
 title = models.CharField(max_length=300)
 selling_price = models.FloatField()
 discounted_price = models.FloatField()
 description = models.TextField()
 brand = models.CharField(max_length=100)
 category = models.CharField( choices=CATEGORY_CHOICES, max_length=10)
 img_link = models.URLField(blank=True, null=True) 
 product_image = models.ImageField(upload_to='productimg',blank=True, null=True)
 location = models.CharField(max_length=255, blank=True, null=True)  # e.g. "Mumbai, India"
 is_active = models.BooleanField(default=True)

 def __str__(self):
  return str(self.id)

class ProductRating(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	rating = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(5)])
	review = models.TextField(blank=True)
	timestamp = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f'{self.user.username} rated {self.product.title}'


class Interaction(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	event_type = models.CharField(max_length=20, choices=[
		('viewed', 'Viewed'),
		('added_to_cart', 'Added to Cart'),
		('purchased', 'Purchased'),
		('searched', 'Searched'),
	])
	timestamp = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f'{self.user.username} {self.event_type} {self.product.title}'


class Cart(models.Model):
 user = models.ForeignKey(User, on_delete=models.CASCADE)
 product = models.ForeignKey(Product, on_delete=models.CASCADE)
 quantity = models.PositiveIntegerField(default=1)

 def __str__(self):
  return str(self.id)
  
  # Below Property will be used by checkout.html page to show total cost in order summary
 @property
 def total_cost(self):
   return self.quantity * self.product.discounted_price

STATUS_CHOICES = (
	('Pending', 'Pending'),
	('Accepted', 'Accepted'),
	('Packed', 'Packed'),
	('On Way', 'On Way'),
	('Out for Delivery', 'Out for Delivery'),
	('Delivered', 'Delivered'),
	('Cancelled', 'Cancelled'),
)




class OrderPlaced(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField(default=1)
	ordered_date = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
	eta = models.DateField(default=date.today)
	updated_at = models.DateTimeField(auto_now=True)

	def get_delivery_estimate(self):
		status_days_map = {
			'Pending': 4,
			'Accepted': 3,
			'Packed': 2,
			'Out for Delivery': 1,
			'Delivered': 0,
		}

		if self.status == 'Delivered':
			return "Order Delivered ✅"
		
		days_to_add = status_days_map.get(self.status)
		if days_to_add is not None:
			delivery_date = self.eta + timedelta(days=days_to_add)
			return f"Estimated delivery on {delivery_date.strftime('%d %b %Y')}"
		
		return "Delivery info not available for this status."

	@property
	def total_cost(self):
		return self.quantity * self.product.discounted_price


class Profile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	image = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg')

	def __str__(self):
		return f'{self.user.username} Profile'
	
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
	if created:
		Profile.objects.create(user=instance)
	else:
		instance.profile.save()


from django.db import models
from django.contrib.auth.models import User
from app.models import Product

class RecommendationLog(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	timestamp = models.DateTimeField(auto_now_add=True)
	source = models.CharField(max_length=100, default="recommend_view")  # Optional: distinguish views
