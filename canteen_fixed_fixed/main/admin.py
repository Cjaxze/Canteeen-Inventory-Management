from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html
from .models import UserProfile, Category, InventoryItem, StockTransaction, Contact


# ── Patch default AdminSite with dashboard data ────────────────────────────────

_original_index = admin.AdminSite.index

def _canteen_index(self, request, extra_context=None):
    items = InventoryItem.objects.select_related('category').all()
    total_value = sum(i.price * i.quantity for i in items)
    low_stock_items = [i for i in items if i.is_low_stock and i.quantity > 0]
    today = timezone.now().date()
    today_txns = StockTransaction.objects.filter(timestamp__date=today).count()
    users = User.objects.select_related('profile').all()
    recent_transactions = StockTransaction.objects.select_related(
        'item', 'recorded_by'
    ).order_by('-timestamp')[:10]

    extra_context = extra_context or {}
    extra_context.update({
        'total_items': items.count(),
        'low_stock_count': len(low_stock_items),
        'out_of_stock_count': items.filter(quantity=0).count(),
        'total_value': total_value,
        'low_stock_items': low_stock_items[:5],
        'recent_transactions': recent_transactions,
        'today_txns': today_txns,
        'employee_count': users.filter(profile__role='employee').count(),
        'owner_count': users.filter(profile__role='admin').count(),
        'category_count': Category.objects.count(),
    })
    return _original_index(self, request, extra_context)

admin.AdminSite.index = _canteen_index


# ── Inline ─────────────────────────────────────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('role',)


# ── User Admin ─────────────────────────────────────────────────────────────────

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_role', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'profile__role')

    def get_role(self, obj):
        try:
            role = obj.profile.role
            color = '#e8794a' if role == 'admin' else '#6b9ed2'
            display = 'OWNER' if role == 'admin' else role.upper()
            return format_html(
                '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
                color, display
            )
        except Exception:
            return '—'
    get_role.short_description = 'Role'


# ── Category Admin ─────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'item_count')
    search_fields = ('name',)

    def item_count(self, obj):
        count = obj.inventoryitem_set.count()
        return format_html('<strong>{}</strong> items', count)
    item_count.short_description = 'Items'


# ── InventoryItem Admin ────────────────────────────────────────────────────────

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity_badge', 'price', 'status_badge', 'last_updated')
    list_filter = ('category',)
    search_fields = ('name', 'description')
    readonly_fields = ('date_added', 'last_updated')

    fieldsets = (
        ('Item Info', {'fields': ('name', 'category', 'description')}),
        ('Stock', {'fields': ('quantity', 'unit', 'low_stock_threshold')}),
        ('Pricing', {'fields': ('price',)}),
        ('Timestamps', {'fields': ('date_added', 'last_updated'), 'classes': ('collapse',)}),
    )

    def quantity_badge(self, obj):
        return format_html('{} {}', obj.quantity, obj.unit)
    quantity_badge.short_description = 'Qty'

    def status_badge(self, obj):
        if obj.quantity == 0:
            return format_html(
                '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
                '#b52a2a', 'OUT'
            )
        elif obj.is_low_stock:
            return format_html(
                '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
                '#b5852a', 'LOW'
            )
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
            '#2a7a4b', 'OK'
        )

    status_badge.short_description = 'Status'


# ── StockTransaction Admin ─────────────────────────────────────────────────────

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('item', 'type_badge', 'quantity', 'recorded_by', 'timestamp', 'note')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('item__name', 'note')
    readonly_fields = ('timestamp',)

    def type_badge(self, obj):
        if obj.transaction_type == 'in':
            return format_html(
                '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
                '#2a7a4b', 'IN'
            )
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
            '#b52a2a', 'OUT'
        )
    type_badge.short_description = 'Type'


# ── Contact Admin ──────────────────────────────────────────────────────────────

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'message')
    search_fields = ('name', 'email')


# ── Register with default admin site ──────────────────────────────────────────

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.site_header = "CanteenIMS Administration"
admin.site.site_title = "CanteenIMS"
admin.site.index_title = "Dashboard"