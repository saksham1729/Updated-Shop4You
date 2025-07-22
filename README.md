🛍️ Shop4You — Django E-Commerce Website

Shop4You is a full-stack e-commerce web application built using Django, offering core features like product listing, cart functionality, customer authentication, checkout with address selection, and OTP/email-based user registration.
✨ Features

  🔐 User Authentication: Register, login, and secure password management

  📧 Email OTP Verification: OTP sent to email during registration

  🛒 Shopping Cart: Add, update, and remove products from the cart

  📦 Product Categories: Browse by Top Wear, Bottom Wear, Mobiles, Laptops

  💳 Checkout System: Shipping address selection and order placement

  📬 Email Notifications: On login, password reset, and order placement (via Mailtrap)

  📄 Order History: View past orders with dynamic progress tracking

  📷 Image Handling: Product images with consistent styling using Bootstrap

  🔍 Price & Brand Filters: Filter products by price range or brand

  📊 Dynamic Quantity Management: AJAX-based cart quantity updates

🛠️ Tech Stack

  Backend: Django 4.x

  Frontend: HTML, CSS, Bootstrap 5

  Database: SQLite (default, can be upgraded to PostgreSQL)

  Email Service: Mailtrap (for development/testing)

  Other: jQuery (for cart interactivity), Django Messages framework

🚀 Setup Instructions

 #Clone the Repository

git clone https://github.com/your-username/shoppinglyx.git
cd shoppinglyx

#Create and Activate Virtual Environment

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

#Install Dependencies

pip install -r requirements.txt

#Configure Mailtrap in settings.py

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.mailtrap.io'
EMAIL_HOST_USER = 'your_mailtrap_username'
EMAIL_HOST_PASSWORD = 'your_mailtrap_password'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

#Run Migrations

python manage.py makemigrations
python manage.py migrate

#Run the Server

    python manage.py runserver

 #Access the App
    Visit http://127.0.0.1:8000 in your browser.

🧪 Demo Users (Optional)

You can optionally create superusers or demo customers:

python manage.py createsuperuser

📁 Project Structure (Simplified)

shoppinglyx/
│
├── app/                  # Main app with views, models, templates
├── shoppinglyx/          # Project settings and URLs
├── media/                # Uploaded product images
├── static/               # CSS, JS, images
├── templates/            # HTML templates
├── db.sqlite3            # SQLite database
└── manage.py
