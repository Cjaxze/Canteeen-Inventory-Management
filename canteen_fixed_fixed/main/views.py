from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.utils import timezone
from functools import wraps
from .models import Contact, InventoryItem, Category, StockTransaction, UserProfile
import datetime


# The dashboard is open to everyone: there is no login or sign up.

def admin_required(view_func):
    return view_func


# ─── Public Pages ─────────────────────────────────────────────────────────────

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


# ─── ADMIN PANEL ──────────────────────────────────────────────────────────────

@admin_required
def admin_panel(request):
    items = InventoryItem.objects.select_related('category').all()
    total_value = sum(i.price * i.quantity for i in items)
    low_stock_items = [i for i in items if i.is_low_stock and i.quantity > 0]
    recent_transactions = StockTransaction.objects.select_related('item').order_by('-timestamp')[:15]
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
        'categories': categories,
        'all_items': items,
        'today_txns': today_txns,
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
            quantity=qty, note=note, recorded_by=None
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
def admin_transactions(request):
    transactions = StockTransaction.objects.select_related('item').order_by('-timestamp')
    return render(request, 'admin_panel/transactions.html', {'transactions': transactions})
