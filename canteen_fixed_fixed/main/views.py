from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.utils import timezone
from functools import wraps
from .models import Contact, InventoryItem, Category, StockTransaction, UserProfile
import datetime


# ─── Role Decorators ─────────────────────────────────────────────────────────

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        profile = getattr(request.user, 'profile', None)
        if profile and profile.is_admin:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('employee_dashboard')
    return wrapper


def get_role(request):
    profile = getattr(request.user, 'profile', None)
    return profile.role if profile else 'employee'


# ─── Public Pages ─────────────────────────────────────────────────────────────

def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_text = request.POST.get('message')
        Contact.objects.create(name=name, email=email, message=message_text)
        return redirect('home')
    return render(request, 'contact.html')


# ─── EMPLOYEE LOGIN / LOGOUT ──────────────────────────────────────────────────

def employee_login(request):
    # Already logged in as employee → go to dashboard
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.is_admin:
            return redirect('admin_panel')
        return redirect('employee_dashboard')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            profile = getattr(user, 'profile', None)
            if profile and profile.is_admin:
                # Block admins from employee login
                error = 'Owner accounts must use the Owner Portal.'
            else:
                login(request, user)
                return redirect('employee_dashboard')
        else:
            error = 'Invalid username or password.'
    return render(request, 'registration/employee_login.html', {'error': error})


def employee_logout(request):
    if request.method == 'POST':
        logout(request)
    return redirect('employee_login')


# ─── ADMIN LOGIN / LOGOUT ─────────────────────────────────────────────────────

def admin_login(request):
    # Already logged in as admin → go to admin panel
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.is_admin:
            return redirect('admin_panel')
        # Logged in as employee → reject
        return redirect('employee_dashboard')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            profile = getattr(user, 'profile', None)
            if profile and profile.is_admin:
                login(request, user)
                return redirect('admin_panel')
            else:
                error = 'This portal is for Owner accounts only.'
        else:
            error = 'Invalid credentials.'
    return render(request, 'registration/admin_login.html', {'error': error})


def admin_logout(request):
    if request.method == 'POST':
        logout(request)
    return redirect('admin_login')


# ─── SIGNUP (creates employee by default) ────────────────────────────────────

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created. You can now log in.')
            return redirect('employee_login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


# ─── EMPLOYEE DASHBOARD (shared inventory) ───────────────────────────────────

@login_required(login_url='/staff/login/')
def employee_dashboard(request):
    # Admins who land here get pushed to admin panel
    if get_role(request) == 'admin':
        return redirect('admin_panel')

    items = InventoryItem.objects.select_related('category').all()
    low_stock_items = [i for i in items if i.is_low_stock and i.quantity > 0]
    recent_transactions = StockTransaction.objects.select_related('item').filter(
        recorded_by=request.user
    ).order_by('-timestamp')[:10]
    context = {
        'total_items': items.count(),
        'low_stock_count': len(low_stock_items),
        'out_of_stock_count': items.filter(quantity=0).count(),
        'low_stock_items': low_stock_items,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'inventory/employee_dashboard.html', context)


@login_required(login_url='/staff/login/')
def inventory_list(request):
    if get_role(request) == 'admin':
        return redirect('admin_panel')
    items = InventoryItem.objects.select_related('category').all()
    categories = Category.objects.all()
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    if query:
        items = items.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_id:
        items = items.filter(category_id=category_id)
    if status_filter == 'out':
        items = items.filter(quantity=0)
    return render(request, 'inventory/inventory_list.html', {
        'role': 'employee', 'items': items, 'categories': categories,
        'query': query, 'selected_category': category_id, 'status_filter': status_filter,
    })


@login_required(login_url='/staff/login/')
def stock_transaction(request, pk):
    if get_role(request) == 'admin':
        return redirect('admin_panel')
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        txn_type = request.POST.get('type')
        qty = int(request.POST.get('quantity', 0))
        note = request.POST.get('note', '')
        if txn_type == 'in':
            messages.error(request, 'Employees can only record stock-out transactions.')
            return redirect('stock_transaction', pk=pk)
        if qty > item.quantity:
            messages.error(request, 'Not enough stock!')
            return redirect('stock_transaction', pk=pk)
        item.quantity -= qty
        item.save()
        StockTransaction.objects.create(
            item=item, transaction_type='out',
            quantity=qty, note=note, recorded_by=request.user
        )
        messages.success(request, f'Stock removed for "{item.name}".')
        return redirect('inventory_list')
    return render(request, 'inventory/stock_transaction.html', {'item': item, 'role': 'employee'})


@login_required(login_url='/staff/login/')
def transaction_log(request):
    if get_role(request) == 'admin':
        return redirect('admin_panel')
    transactions = StockTransaction.objects.select_related('item').filter(
        recorded_by=request.user
    ).order_by('-timestamp')
    return render(request, 'inventory/transaction_log.html', {
        'transactions': transactions, 'role': 'employee'
    })


@login_required(login_url='/staff/login/')
def search_items(request):
    q = request.GET.get('q', '')
    items = InventoryItem.objects.select_related('category').filter(
        Q(name__icontains=q) | Q(category__name__icontains=q)
    )[:20]
    data = [{'id': i.id, 'name': i.name,
              'category': i.category.name if i.category else '—',
              'quantity': i.quantity, 'unit': i.unit, 'status': i.status} for i in items]
    return JsonResponse({'results': data})


# ─── ADMIN PANEL ──────────────────────────────────────────────────────────────

@admin_required
def admin_panel(request):
    items = InventoryItem.objects.select_related('category').all()
    total_value = sum(i.price * i.quantity for i in items)
    low_stock_items = [i for i in items if i.is_low_stock and i.quantity > 0]
    recent_transactions = StockTransaction.objects.select_related('item', 'recorded_by').order_by('-timestamp')[:15]
    users = User.objects.select_related('profile').all()
    categories = Category.objects.all()
    today = timezone.now().date()
    today_txns = StockTransaction.objects.filter(timestamp__date=today).count()
    context = {
        'total_items': items.count(),
        'low_stock_count': len(low_stock_items),
        'out_of_stock_count': items.filter(quantity=0).count(),
        'total_value': total_value,
        'low_stock_items': low_stock_items,
        'recent_transactions': recent_transactions,
        'users': users,
        'categories': categories,
        'all_items': items,
        'today_txns': today_txns,
        'employee_count': users.filter(profile__role='employee').count(),
        'admin_count': users.filter(profile__role='admin').count(),
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def admin_inventory_list(request):
    items = InventoryItem.objects.select_related('category').all()
    categories = Category.objects.all()
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    if query:
        items = items.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_id:
        items = items.filter(category_id=category_id)
    if status_filter:
        if status_filter == 'out':
            items = items.filter(quantity=0)
        elif status_filter == 'low':
            items = items.exclude(quantity=0).filter(quantity__lte=10)
    return render(request, 'admin_panel/inventory.html', {
        'items': items, 'categories': categories,
        'query': query, 'selected_category': category_id, 'status_filter': status_filter,
    })


@admin_required
def admin_item_add(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Item name is required.')
            return render(request, 'admin_panel/item_form.html', {'categories': categories, 'action': 'Add'})
        category_id = request.POST.get('category', '').strip()
        try:
            quantity = int(request.POST.get('quantity', 0))
        except (ValueError, TypeError):
            quantity = 0
        unit = request.POST.get('unit', 'pcs').strip() or 'pcs'
        try:
            price = float(request.POST.get('price', 0.00))
        except (ValueError, TypeError):
            price = 0.00
        try:
            low_stock_threshold = int(request.POST.get('low_stock_threshold', 10))
        except (ValueError, TypeError):
            low_stock_threshold = 10
        description = request.POST.get('description', '')
        category = None
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                category = None
        InventoryItem.objects.create(
            name=name, category=category, quantity=quantity,
            unit=unit, price=price, low_stock_threshold=low_stock_threshold,
            description=description
        )
        messages.success(request, f'"{name}" added to inventory.')
        next_url = request.POST.get('_next', '').strip() or request.GET.get('next', '').strip()
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect('admin_inventory_list')
    return render(request, 'admin_panel/item_form.html', {'categories': categories, 'action': 'Add'})


@admin_required
def admin_item_edit(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    categories = Category.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Item name is required.')
            return render(request, 'admin_panel/item_form.html', {'item': item, 'categories': categories, 'action': 'Edit'})
        item.name = name
        category_id = request.POST.get('category', '').strip()
        if category_id:
            try:
                item.category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                item.category = None
        else:
            item.category = None
        try:
            item.quantity = int(request.POST.get('quantity', 0))
        except (ValueError, TypeError):
            item.quantity = 0
        item.unit = request.POST.get('unit', 'pcs').strip() or 'pcs'
        try:
            item.price = float(request.POST.get('price', 0.00))
        except (ValueError, TypeError):
            item.price = 0.00
        try:
            item.low_stock_threshold = int(request.POST.get('low_stock_threshold', 10))
        except (ValueError, TypeError):
            item.low_stock_threshold = 10
        item.description = request.POST.get('description', '')
        item.save()
        messages.success(request, f'"{item.name}" updated.')
        return redirect('admin_inventory_list')
    return render(request, 'admin_panel/item_form.html', {'item': item, 'categories': categories, 'action': 'Edit'})


@admin_required
def admin_item_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        name = item.name
        item.delete()
        messages.success(request, f'"{name}" deleted.')
        return redirect('admin_inventory_list')
    return render(request, 'admin_panel/item_confirm_delete.html', {'item': item})


@admin_required
def admin_stock_transaction(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        txn_type = request.POST.get('type')
        qty = int(request.POST.get('quantity', 0))
        note = request.POST.get('note', '')
        if txn_type == 'in':
            item.quantity += qty
        elif txn_type == 'out':
            if qty > item.quantity:
                messages.error(request, 'Not enough stock!')
                return redirect('admin_stock_transaction', pk=pk)
            item.quantity -= qty
        item.save()
        StockTransaction.objects.create(
            item=item, transaction_type=txn_type,
            quantity=qty, note=note, recorded_by=request.user
        )
        messages.success(request, f'Stock {"added" if txn_type == "in" else "removed"} for "{item.name}".')
        # Honour an explicit ?next= (e.g. filtered inventory URL), otherwise
        # fall back to the item's own category filter
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        if item.category_id:
            return redirect(f'/owner/inventory/?category={item.category_id}')
        return redirect('admin_inventory_list')
    return render(request, 'admin_panel/stock_transaction.html', {'item': item})


@admin_required
def admin_categories(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            Category.objects.get_or_create(name=name, defaults={'description': description})
            messages.success(request, f'Category "{name}" created.')
        return redirect('admin_categories')
    return render(request, 'admin_panel/categories.html', {'categories': categories})


@admin_required
def admin_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted.')
    return redirect('admin_categories')


@admin_required
def admin_category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if name:
            category.name = name
            category.description = description
            category.save()
            messages.success(request, f'Category "{name}" updated.')
        return redirect('admin_categories')
    return redirect('admin_categories')


@admin_required
def admin_users(request):
    users = User.objects.select_related('profile').all()
    return render(request, 'admin_panel/users.html', {'users': users})


@admin_required
def admin_user_role_change(request, user_id):
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        new_role = request.POST.get('role')
        if new_role in ['admin', 'employee']:
            profile, _ = UserProfile.objects.get_or_create(user=target_user)
            profile.role = new_role
            profile.save()
            display_role = 'Owner' if new_role == 'admin' else 'Employee'
            messages.success(request, f'{target_user.username} role updated to {display_role}.')
    return redirect('admin_users')


@admin_required
def admin_user_delete(request, user_id):
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        if target_user == request.user:
            messages.error(request, 'You cannot delete your own account.')
        else:
            username = target_user.username
            target_user.delete()
            messages.success(request, f'User "{username}" deleted.')
    return redirect('admin_users')


@admin_required
def admin_transactions(request):
    transactions = StockTransaction.objects.select_related('item', 'recorded_by').order_by('-timestamp')
    return render(request, 'admin_panel/transactions.html', {'transactions': transactions})


# ─── Legacy redirects (old URLs) ─────────────────────────────────────────────

def inventory_dashboard(request):
    if request.user.is_authenticated and get_role(request) == 'admin':
        return redirect('admin_panel')
    return redirect('employee_dashboard')


def user_management(request):
    return redirect('admin_users')


def user_role_change(request, user_id):
    return admin_user_role_change(request, user_id)


def user_delete(request, user_id):
    return admin_user_delete(request, user_id)
