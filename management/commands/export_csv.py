from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.models import Product, Customer, OrderPlaced, Cart, Profile  # adjust 'app' to your app name
import os
import csv

EXPORT_DIR = 'exported_csv'

class Command(BaseCommand):  # ✅ This must be exactly 'Command'
    help = 'Export data from all models to CSV'

    def handle(self, *args, **kwargs):
        os.makedirs(EXPORT_DIR, exist_ok=True)

        def export_csv(filename, queryset, fields, transform=None):
            filepath = os.path.join(EXPORT_DIR, filename)
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(fields)
                for obj in queryset:
                    row = [getattr(obj, field) for field in fields]
                    if transform:
                        row = transform(obj, row)
                    writer.writerow(row)

        export_csv('products.csv', Product.objects.all(), [
            'id', 'title', 'selling_price', 'discounted_price', 'description', 'brand', 'category'
        ])

        export_csv('customers.csv', Customer.objects.all(), [
            'id', 'user_id', 'name', 'locality', 'city', 'zipcode', 'state'
        ])

        export_csv('orders.csv', OrderPlaced.objects.all(), [
            'id', 'user_id', 'customer_id', 'product_id', 'quantity', 'ordered_date', 'status'
        ])

        export_csv('carts.csv', Cart.objects.all(), [
            'id', 'user_id', 'product_id', 'quantity'
        ])

        export_csv('profiles.csv', Profile.objects.all(), [
            'id', 'user_id', 'image'
        ])

        export_csv('users.csv', User.objects.all(), [
            'id', 'username', 'email'
        ], transform=lambda obj, row: [obj.id, obj.username, obj.email or ''])

        self.stdout.write(self.style.SUCCESS("✅ All CSVs exported successfully."))
