from django.contrib import admin
from django.urls import path
from main import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Public ──
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    # ── Employee Auth ──
    path('staff/login/', views.employee_login, name='employee_login'),
    path('staff/logout/', views.employee_logout, name='employee_logout'),
    path('staff/signup/', views.signup, name='signup'),

    # ── Admin Auth (separate portal) ──
    path('owner/login/', views.admin_login, name='admin_login'),
    path('owner/logout/', views.admin_logout, name='admin_logout'),

    # ── Employee-facing inventory ──
    path('inventory/', views.employee_dashboard, name='employee_dashboard'),
    path('inventory/list/', views.inventory_list, name='inventory_list'),
    path('inventory/stock/<int:pk>/', views.stock_transaction, name='stock_transaction'),
    path('inventory/transactions/', views.transaction_log, name='transaction_log'),
    path('inventory/search/', views.search_items, name='search_items'),

    # ── Admin Panel ──
    path('owner/', views.admin_panel, name='admin_panel'),
    path('owner/inventory/', views.admin_inventory_list, name='admin_inventory_list'),
    path('owner/inventory/add/', views.admin_item_add, name='admin_item_add'),
    path('owner/inventory/edit/<int:pk>/', views.admin_item_edit, name='admin_item_edit'),
    path('owner/inventory/delete/<int:pk>/', views.admin_item_delete, name='admin_item_delete'),
    path('owner/inventory/stock/<int:pk>/', views.admin_stock_transaction, name='admin_stock_transaction'),
    path('owner/categories/', views.admin_categories, name='admin_categories'),
    path('owner/categories/delete/<int:pk>/', views.admin_category_delete, name='admin_category_delete'),
    path('owner/categories/edit/<int:pk>/', views.admin_category_edit, name='admin_category_edit'),
    path('owner/users/', views.admin_users, name='admin_users'),
    path('owner/users/<int:user_id>/role/', views.admin_user_role_change, name='admin_user_role_change'),
    path('owner/users/<int:user_id>/delete/', views.admin_user_delete, name='admin_user_delete'),
    path('owner/transactions/', views.admin_transactions, name='admin_transactions'),

    # ── Legacy redirects ──
    path('login/', views.employee_login, name='login'),
    path('signup/', views.signup, name='signup_legacy'),
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/role/', views.user_role_change, name='user_role_change'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
]
