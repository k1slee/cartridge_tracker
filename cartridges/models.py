from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

class Location(models.Model):
    LOCATION_TYPES = [
        ('warehouse', 'Склад'),
        ('office', 'Офис'),
        ('service', 'Сервисный центр'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Название')
    type = models.CharField(max_length=20, choices=LOCATION_TYPES, verbose_name='Тип')
    contact_person = models.CharField(max_length=100, verbose_name='Контактное лицо', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Телефон', blank=True)
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    class Meta:
        verbose_name = 'Локация'
        verbose_name_plural = 'Локации'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

class CartridgeModel(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название модели')
    manufacturer = models.CharField(max_length=100, verbose_name='Производитель')
    compatible_printers = models.TextField(verbose_name='Совместимые принтеры', blank=True)
    max_refills = models.IntegerField(default=5, verbose_name='Максимальное количество заправок')
    refill_instructions = models.TextField(blank=True, verbose_name='Инструкции по заправке')
    
    class Meta:
        verbose_name = 'Модель картриджа'
        verbose_name_plural = 'Модели картриджей'
        ordering = ['manufacturer', 'name']
    
    def __str__(self):
        return f"{self.manufacturer} {self.name}"

class Printer(models.Model):
    PRINTER_TYPES = [
        ('laser', 'Лазерный'),
        ('inkjet', 'Струйный'),
        ('multifunction', 'МФУ'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Название')
    model = models.CharField(max_length=100, verbose_name='Модель')
    serial_number = models.CharField(max_length=100, unique=True, verbose_name='Серийный номер')
    printer_type = models.CharField(max_length=20, choices=PRINTER_TYPES, verbose_name='Тип принтера')
    is_inkjet = models.BooleanField(default=False, verbose_name='На чернилах')  
    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name='Локация')
    installation_date = models.DateField(default=timezone.now, verbose_name='Дата установки')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    
    class Meta:
        verbose_name = 'Принтер'
        verbose_name_plural = 'Принтеры'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.model} ({self.serial_number})"

class Cartridge(models.Model):
    CONSUMABLE_TYPES = [
        ('cartridge', 'Картридж'),
        ('drum', 'Барабан'),
    ]
    
    STATUS_CHOICES = [
        ('in_stock', 'На складе'),
        ('in_transit', 'В пути'),
        ('at_service', 'На заправке'),
        ('in_reserve', 'В резерве'),
        ('installed', 'Установлен'),
        ('disposed', 'Списан'),
    ]
    
    CONDITION_CHOICES = [
        ('new', 'Новый'),
        ('working', 'Рабочий'),
        ('needs_repair', 'Требует ремонта'),
        ('refilled', 'Заправлен'),
    ]
    
    serial_number = models.CharField(max_length=100, unique=True, verbose_name='Серийный номер')
    consumable_type = models.CharField(
        max_length=20, 
        choices=CONSUMABLE_TYPES, 
        default='cartridge', 
        verbose_name='Тип расходника'
    )
    model = models.ForeignKey(CartridgeModel, on_delete=models.PROTECT, verbose_name='Модель')
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_stock', verbose_name='Текущий статус')
    current_location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name='Текущая локация')
    installed_in_printer = models.ForeignKey(Printer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Установлен в принтере')
    date_of_introduction = models.DateField(default=timezone.now, verbose_name='Дата ввода в эксплуатацию')
    refill_count = models.IntegerField(default=0, verbose_name='Количество заправок')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new', verbose_name='Состояние')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Расходник'
        verbose_name_plural = 'Расходники'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['serial_number']),
            models.Index(fields=['current_status']),
            models.Index(fields=['consumable_type']),
        ]
    
    def __str__(self):
        type_display = "Барабан" if self.consumable_type == 'drum' else "Картридж"
        return f"{type_display} {self.model} - {self.serial_number}"
    
    def clean(self):
        if self.installed_in_printer and self.current_status in ['at_service', 'disposed']:
            raise ValidationError('Нельзя установить расходник со статусом "На заправке" или "Списан"')
        
        if self.refill_count > self.model.max_refills:
            self.condition = 'needs_repair'

class Operation(models.Model):
    OPERATION_TYPES = [
        ('receipt', 'Поступление'),
        ('issue_service', 'Выдача на заправку'),
        ('receive_service', 'Приём с заправки'),
        ('install', 'Установка в принтер'),
        ('remove', 'Снятие с принтера'),
        ('transfer', 'Перемещение'),
        ('dispose', 'Списание'),
    ]
    
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name='Тип операции')
    cartridge = models.ForeignKey(Cartridge, on_delete=models.CASCADE, verbose_name='Картридж')
    from_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='operations_from', verbose_name='Откуда')
    to_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='operations_to', verbose_name='Куда')
    printer = models.ForeignKey(Printer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Принтер')
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Пользователь')
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='Дата и время')
    reason = models.TextField(blank=True, verbose_name='Причина')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    
    class Meta:
        verbose_name = 'Операция'
        verbose_name_plural = 'Операции'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.cartridge} - {self.timestamp.strftime('%d.%m.%Y %H:%M')}"
    
    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        
        if is_new:
            self.update_cartridge_status()
    
    def update_cartridge_status(self):
        cartridge = self.cartridge
        operation_type = self.operation_type
        
        status_mapping = {
            'receipt': 'in_stock',
            'issue_service': 'at_service',
            'receive_service': 'in_stock',
            'install': 'installed',
            'remove': 'in_stock',
            'transfer': 'in_transit',
            'dispose': 'disposed',
        }
        
        if operation_type in status_mapping:
            cartridge.current_status = status_mapping[operation_type]
            cartridge.current_location = self.to_location
            
            if operation_type == 'install':
                cartridge.installed_in_printer = self.printer
            elif operation_type == 'remove':
                cartridge.installed_in_printer = None
            elif operation_type == 'receive_service':
                cartridge.refill_count += 1
                cartridge.condition = 'refilled'
            
            cartridge.save()