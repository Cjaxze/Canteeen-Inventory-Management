from django.contrib import admin
from django.urls import path
from main import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Dashboard is the landing page (no login / sign up) ──
    path('', views.admin_panel, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    path('owner/', views.admin_panel, name='admin_panel'),
    path('owner/inventory/', views.admin_inventory_list, name='admin_inventory_list'),
    path('owner/inventory/add/', views.admin_item_add, name='admin_item_add'),
    path('owner/inventory/edit/<int:pk>/', views.admin_item_edit, name='admin_item_edit'),
    path('owner/inventory/delete/<int:pk>/', views.admin_item_delete, name='admin_item_delete'),
    path('owner/inventory/stock/<int:pk>/', views.admin_stock_transaction, name='admin_stock_transaction'),
    path('owner/categories/', views.admin_categories, name='admin_categories'),
    path('owner/categories/delete/<int:pk>/', views.admin_category_delete, name='admin_category_delete'),
    path('owner/categories/edit/<int:pk>/', views.admin_category_edit, name='admin_category_edit'),
    path('owner/transactions/', views.admin_transactions, name='admin_transactions'),
]
