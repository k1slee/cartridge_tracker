from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, F
from django.http import JsonResponse
from .models import Cartridge, Operation, CartridgeModel, Location, Printer
from .forms import OperationForm, CartridgeForm, PrinterForm
from django.http import JsonResponse
@login_required
def dashboard(request):
    """Главная панель управления с учётом типов расходников"""
   
    stats = {
        'total_consumables': Cartridge.objects.count(),
        'total_cartridges': Cartridge.objects.filter(consumable_type='cartridge').count(),
        'total_drums': Cartridge.objects.filter(consumable_type='drum').count(),
        'cartridges_in_stock': Cartridge.objects.filter(consumable_type='cartridge', current_status='in_stock').count(),
        'drums_in_stock': Cartridge.objects.filter(consumable_type='drum', current_status='in_stock').count(),
        'cartridges_installed': Cartridge.objects.filter(consumable_type='cartridge', current_status='installed').count(),
        'drums_installed': Cartridge.objects.filter(consumable_type='drum', current_status='installed').count(),
        'at_service': Cartridge.objects.filter(current_status='at_service').count(),
        'needs_repair': Cartridge.objects.filter(condition='needs_repair').count(),
    }
    
   
    recent_operations = Operation.objects.select_related('cartridge', 'user')[:10]
    
    
    attention_consumables = Cartridge.objects.filter(
        Q(condition='needs_repair') | 
        Q(refill_count__gte=F('model__max_refills'))
    )[:8]
    
    context = {
        'stats': stats,
        'recent_operations': recent_operations,
        'attention_consumables': attention_consumables,
    }
    return render(request, 'cartridges/dashboard.html', context)

@login_required
def cartridge_list(request):
    """Список всех расходников с фильтрацией по типу"""
    consumables = Cartridge.objects.select_related('model', 'current_location', 'installed_in_printer')
    
  
    consumable_type = request.GET.get('consumable_type')
    status = request.GET.get('status')
    model_id = request.GET.get('model')
    location_id = request.GET.get('location')
    
    if consumable_type:
        consumables = consumables.filter(consumable_type=consumable_type)
    if status:
        consumables = consumables.filter(current_status=status)
    if model_id:
        consumables = consumables.filter(model_id=model_id)
    if location_id:
        consumables = consumables.filter(current_location_id=location_id)
    
    context = {
        'consumables': consumables,
        'models': CartridgeModel.objects.all(),
        'locations': Location.objects.filter(is_active=True),
        'consumable_type_choices': Cartridge.CONSUMABLE_TYPES,
        'status_choices': Cartridge.STATUS_CHOICES,
    }
    return render(request, 'cartridges/cartridge_list.html', context)

@login_required
def cartridge_detail(request, pk):
    """Детальная информация о расходнике"""
    cartridge = get_object_or_404(
        Cartridge.objects.select_related('model', 'current_location', 'installed_in_printer'), 
        pk=pk
    )
    
    operations = Operation.objects.filter(cartridge=cartridge).select_related(
        'user', 'from_location', 'to_location', 'printer'
    ).order_by('-timestamp')
    
    context = {
        'cartridge': cartridge,
        'operations': operations,
    }
    return render(request, 'cartridges/cartridge_detail.html', context)

@login_required
def cartridge_create(request):
    """Добавление нового расходника"""
    if request.method == 'POST':
        form = CartridgeForm(request.POST)
        if form.is_valid():
            cartridge = form.save()
            
            
            Operation.objects.create(
                operation_type='receipt',
                cartridge=cartridge,
                from_location=cartridge.current_location,
                to_location=cartridge.current_location,
                user=request.user,
                reason='Первоначальное поступление в систему'
            )
            
            consumable_type_display = 'Барабан' if cartridge.consumable_type == 'drum' else 'Картридж'
            messages.success(request, f'{consumable_type_display} {cartridge.serial_number} успешно добавлен')
            return redirect('cartridges:cartridge_detail', pk=cartridge.pk)  
    else:
        form = CartridgeForm()
    
    context = {'form': form}
    return render(request, 'cartridges/cartridge_form.html', context)

@login_required
def operation_create(request, cartridge_pk=None):
    """Создание операции"""
    cartridge = None
    if cartridge_pk:
        cartridge = get_object_or_404(Cartridge, pk=cartridge_pk)
    
    if request.method == 'POST':
        form = OperationForm(request.POST)
        if form.is_valid():
            operation = form.save(commit=False)
            operation.user = request.user
            operation.save()
            
            messages.success(request, f'Операция "{operation.get_operation_type_display()}" успешно создана')
            return redirect('cartridges:cartridge_detail', pk=operation.cartridge.pk)  
    else:
        initial = {'cartridge': cartridge} if cartridge else {}
        form = OperationForm(initial=initial)
    
    context = {
        'form': form,
        'cartridge': cartridge,
    }
    return render(request, 'cartridges/operation_form.html', context)

@login_required
def get_cartridge_info(request, cartridge_id):
    """API для получения информации о картридже (для AJAX)"""
    cartridge = get_object_or_404(Cartridge, pk=cartridge_id)
    data = {
        'serial_number': cartridge.serial_number,
        'model': str(cartridge.model),
        'current_status': cartridge.get_current_status_display(),
        'current_location': str(cartridge.current_location),
        'refill_count': cartridge.refill_count,
    }
    return JsonResponse(data)

@login_required
def printer_list(request):
    """Список всех принтеров"""
    printers = Printer.objects.select_related('location')
    
    # Фильтрация
    printer_type = request.GET.get('printer_type')
    is_inkjet = request.GET.get('is_inkjet')
    location_id = request.GET.get('location')
    
    if printer_type:
        printers = printers.filter(printer_type=printer_type)
    if is_inkjet:
        printers = printers.filter(is_inkjet=True)
    if location_id:
        printers = printers.filter(location_id=location_id)
    
    context = {
        'printers': printers,
        'locations': Location.objects.filter(is_active=True),
        'printer_type_choices': Printer.PRINTER_TYPES,
    }
    return render(request, 'cartridges/printer_list.html', context)

@login_required
def printer_detail(request, pk):
    """Детальная информация о принтере"""
    printer = get_object_or_404(Printer.objects.select_related('location'), pk=pk)
    
    
    installed_consumables = Cartridge.objects.filter(installed_in_printer=printer)
    
    context = {
        'printer': printer,
        'installed_consumables': installed_consumables,
    }
    return render(request, 'cartridges/printer_detail.html', context)

@login_required
def printer_create(request):
    """Добавление нового принтера"""
    if request.method == 'POST':
        form = PrinterForm(request.POST)
        if form.is_valid():
            printer = form.save()
            messages.success(request, f'Принтер {printer.name} успешно добавлен')
            return redirect('cartridges:printer_detail', pk=printer.pk)  
    else:
        form = PrinterForm()
    
    context = {'form': form}
    return render(request, 'cartridges/printer_form.html', context)

@login_required
def get_printers_by_location(request):
    """API для получения принтеров по локации"""
    location_id = request.GET.get('location_id')
    
    if location_id:
        printers = Printer.objects.filter(location_id=location_id, is_active=True)
        printers_data = [
            {'id': printer.id, 'name': f"{printer.name} ({printer.model})"}
            for printer in printers
        ]
    else:
        printers_data = []
    
    return JsonResponse({'printers': printers_data})


@login_required
def get_locations_by_operation_type(request):
    """API для получения локаций по типу операции"""
    operation_type = request.GET.get('operation_type')
    
    if operation_type == 'install':
        # Для установки показываем только локации с принтерами
        locations_with_printers = Location.objects.filter(
            printer__is_active=True
        ).distinct()
        locations_data = [
            {'id': loc.id, 'name': loc.name}
            for loc in locations_with_printers
        ]
    else:
        # Для других операций показываем все активные локации
        locations = Location.objects.filter(is_active=True)
        locations_data = [
            {'id': loc.id, 'name': loc.name}
            for loc in locations
        ]
    
    return JsonResponse({'locations': locations_data})