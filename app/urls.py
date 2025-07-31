from django.urls import path
from app import views
from app.views import ProductView
from django.conf import settings
from django.conf.urls.static import static

from app.views import recommend_view

from .views import track_order
from .views import chatbot_query
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from .forms import LoginForm, MyPasswordChangeForm, MyPasswordResetForm, MySetPasswordForm
urlpatterns = [
    # path('', views.home),
    path('', views.ProductView.as_view(), name="home"),
    # path('product-detail', views.product_detail, name='product-detail'),
    path('product-detail/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('add-to-cart/', views.add_to_cart, name='add-to-cart'),
    path('cart/', views.show_cart, name='showcart'),
    path('pluscart/', views.plus_cart),
    path('minuscart/', views.minus_cart),
    path('removecart/', views.remove_cart),
    path('checkout/', views.checkout, name='checkout'),
    path('address/', views.address, name='address'),
    path('orders/', views.orders, name='orders'),
    path('paymentdone/?custid=5', views.payment_done, name='paymentdone'),
    path('', ProductView.as_view(), name='home'),
    path('orders/<int:order_id>/track/', track_order, name='track-order'),


    path('mobile/', views.mobile, name='mobile'),
    path('mobile/<slug:data>', views.mobile, name='mobiledata'),

    path('laptop/', views.laptop, name='laptop'),
    path('laptop/<slug:data>/', views.laptop, name='laptopdata'),

    path('topwear/', views.topwear, name='topwear'),
    path('topwear/<slug:data>/', views.topwear, name='topweardata'),

    path('bottomwear/', views.bottomwear, name='bottomwear'),
    path('bottomwear/<slug:data>/', views.bottomwear, name='bottomweardata'),

    path('cables/', views.cables, name='cables'),
    path('cables/<slug:data>/', views.cables, name='cabledata'),

    path('television/', views.television, name='television'),
    path('television/<slug:data>/', views.television, name='televisiondata'),


    path('office/', views.office, name='office'),
    path('office/<slug:data>/', views.office, name='officedata'),

    path('kitchen/', views.kitchen, name='kitchen'),
    path('kitchen/<slug:data>/', views.kitchen, name='kitchendata'),


        path('fans/', views.fans, name='fans'),
    path('fans/<slug:data>/', views.fans, name='fansdata'),

        path('iron/', views.iron, name='iron'),
    path('iron/<slug:data>/', views.iron, name='irondata'),

        path('grinder/', views.grinder, name='grinder'),
    path('grinder/<slug:data>/', views.grinder, name='grinderdata'),

        path('roomheater/', views.roomheater, name='roomheater'),
    path('roomheater/<slug:data>/', views.roomheater, name='roomheaterdata'),

    path('waterheater/', views.waterheater, name='waterheater'),
    path('waterheater/<slug:data>/', views.waterheater, name='waterheaterdata'),




    path('recommend/<int:user_id>/', recommend_view),

    path('accounts/login/', auth_views.LoginView.as_view(template_name='app/login.html', authentication_form=LoginForm), name='login'),
    # path('profile/', views.profile, name='profile'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('passwordchange/', auth_views.PasswordChangeView.as_view(template_name='app/passwordchange.html', form_class=MyPasswordChangeForm, success_url='/passwordchangedone/'), name='passwordchange'),
    path('passwordchangedone/', auth_views.PasswordChangeDoneView.as_view(template_name='app/passwordchangedone.html'), name='passwordchangedone'),
    
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name='app/password_reset.html', form_class=MyPasswordResetForm), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name='app/password_reset_done.html'), name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name='app/password_reset_confirm.html', form_class=MySetPasswordForm), name="password_reset_confirm"),
    path("password-reset-complete/", auth_views.PasswordResetCompleteView.as_view(template_name='app/password_reset_complete.html'), name="password_reset_complete"),


    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),

    path('payment-success/', views.paymentSuccess, name='payment-success'),
    path('payment-cancel/', views.paymentCancel, name='payment-cancel'),

    path('registration/', views.CustomerRegistrationView.as_view(), name='customerregistration'),

    path('search/', views.search_products, name='search-products'),
    path('api/chatbot/', chatbot_query, name='chatbot_query'),


    path('registration/', views.CustomerRegistrationView.as_view(), name='customerregistration'),

    path('rate-product/<int:product_id>/', views.submit_rating, name='submit_rating'),


    path('search/', views.search_products, name='search-products'),
    path('api/chatbot/', chatbot_query, name='chatbot_query'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
