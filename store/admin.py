from django.contrib import admin
from .models import *

# Register your models here.

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    show_change_link = True

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'category', 'modified_date', 'is_available')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]

    def price(self, obj):
        # Initial MVP logic, show min price
        min_price = obj.productvariant_set.aggregate(models.Min('price'))['price__min']
        return min_price if min_price else "N/A"
    
    def stock(self, obj):
         total_stock = obj.productvariant_set.aggregate(models.Sum('stock'))['stock__sum']
         return total_stock if total_stock else 0

    def is_available(self, obj):
        return self.stock(obj) > 0
    is_available.boolean = True

class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'parent_category', 'slug')

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'is_blocked', 'created_at')

class ReviewMediaInline(admin.TabularInline):
    model = ReviewMedia
    extra = 1

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'customer', 'rating', 'created_at', 'is_deleted')
    list_filter = ('rating', 'created_at', 'is_deleted')
    search_fields = ('product__name', 'customer__user__email', 'comment')
    inlines = [ReviewMediaInline]

admin.site.register(User)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVariant)
admin.site.register(Color)
admin.site.register(Size)
admin.site.register(ShippingAddress)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Complaint)
admin.site.register(AttributeRequest)
