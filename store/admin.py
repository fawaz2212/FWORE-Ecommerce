
from django.contrib import admin
from .models import Product, Wishlist, Category
from .models import Order, OrderItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'price',
        'available',
        'created_at'
    )

    list_filter = ('category', 'available')
    search_fields = ('name', 'description')


admin.site.register(Wishlist)
admin.site.register(Order)
admin.site.register(OrderItem)
