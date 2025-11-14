from django.contrib import admin
from .models import CartridgeModel, Location, Printer, Cartridge, Operation

@admin.register(CartridgeModel)
class CartridgeModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'manufacturer', 'max_refills']
    list_filter = ['manufacturer']
    search_fields = ['name', 'manufacturer']
    
    fieldsets = [
        (None, {
            'fields': ['name', 'manufacturer']
        }),
        ('Дополнительно', {
            'fields': ['compatible_printers', 'max_refills', 'refill_instructions'],
            'classes': ['collapse']
        })
    ]

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'is_active']  
    list_filter = ['type', 'is_active']
    search_fields = ['name']  
    list_editable = ['is_active']
    

    fieldsets = [
        (None, {
            'fields': ['name', 'type', 'is_active']
        }),
        ('Контактная информация', {
            'fields': ['contact_person', 'phone'],
            'classes': ['collapse']
        })
    ]

@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ['name', 'model', 'serial_number', 'printer_type', 'is_inkjet', 'location', 'is_active']
    list_filter = ['printer_type', 'is_inkjet', 'location', 'is_active']
    search_fields = ['name', 'model', 'serial_number']
    list_editable = ['is_active', 'is_inkjet']
    
    fieldsets = [
        (None, {
            'fields': ['name', 'model', 'serial_number', 'printer_type', 'is_inkjet']
        }),
        ('Размещение', {
            'fields': ['location', 'installation_date']
        }),
        ('Дополнительно', {
            'fields': ['is_active', 'notes'],
            'classes': ['collapse']
        })
    ]

@admin.register(Cartridge)
class CartridgeAdmin(admin.ModelAdmin):
    list_display = ['serial_number', 'consumable_type', 'model', 'current_status', 'current_location', 'refill_count', 'condition']
    list_filter = ['consumable_type', 'current_status', 'condition', 'model', 'current_location']
    search_fields = ['serial_number', 'model__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        (None, {
            'fields': ['serial_number', 'consumable_type', 'model', 'current_status', 'current_location']
        }),
        ('Статистика', {
            'fields': ['refill_count', 'condition'],
            'classes': ['collapse']
        }),
        ('Дополнительно', {
            'fields': ['installed_in_printer', 'date_of_introduction', 'notes'],
            'classes': ['collapse']
        })
    ]

@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ['operation_type', 'cartridge', 'from_location', 'to_location', 'user', 'timestamp']
    list_filter = ['operation_type', 'timestamp']
    search_fields = ['cartridge__serial_number', 'user__username']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'