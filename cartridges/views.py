from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, F
from django.http import JsonResponse
from .models import Cartridge, Operation, CartridgeModel, Location, Printer
from .forms import OperationForm, CartridgeForm, PrinterForm
from django.http import JsonResponse
from django.utils import timezone
@login_required
def dashboard(request):
    """Главная панель управления с учётом типов расходников"""
    # Обновлённая статистика
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
    
    # Последние операции
    recent_operations = Operation.objects.select_related('cartridge', 'user')[:10]
    
    # Картриджи и барабаны, требующие внимания
    attention_consumables = Cartridge.objects.filter(
        Q(condition='needs_repair') | 
        Q(refill_count__gte=F('model__max_refills'))
    ).order_by('-condition', '-refill_count')
    
    # Дополнительная статистика для кнопки
    needs_repair_count = Cartridge.objects.filter(
        condition='needs_repair',
        current_status__in=['in_stock', 'installed']
    ).count()
    
    max_refills_count = Cartridge.objects.filter(
        refill_count__gte=F('model__max_refills'),
        condition='needs_repair'
    ).count()
    
    context = {
        'stats': stats,
        'recent_operations': recent_operations,
        'attention_consumables': attention_consumables,
        'needs_repair_count': needs_repair_count,
        'max_refills_count': max_refills_count,
    }
    return render(request, 'cartridges/dashboard.html', context)


@login_required
def cartridge_list(request):
    """Список всех расходников с фильтрацией по типу"""
    consumables = Cartridge.objects.select_related('model', 'current_location', 'installed_in_printer')
    
    # Применяем фильтры
    consumable_type = request.GET.get('consumable_type')
    status = request.GET.get('status')
    model_id = request.GET.get('model')
    location_id = request.GET.get('location')
    condition = request.GET.get('condition')
    needs_attention = request.GET.get('needs_attention')
    
    if consumable_type:
        consumables = consumables.filter(consumable_type=consumable_type)
    if status:
        consumables = consumables.filter(current_status=status)
    if model_id:
        consumables = consumables.filter(model_id=model_id)
    if location_id:
        consumables = consumables.filter(current_location_id=location_id)
    if condition:
        consumables = consumables.filter(condition=condition)
    if needs_attention:
        # Фильтр для "требуют внимания"
        consumables = consumables.filter(
            Q(condition='needs_repair') | 
            Q(refill_count__gte=F('model__max_refills'))
        )
    
    context = {
        'consumables': consumables,
        'models': CartridgeModel.objects.all(),
        'locations': Location.objects.filter(is_active=True),
        'consumable_type_choices': Cartridge.CONSUMABLE_TYPES,
        'status_choices': Cartridge.STATUS_CHOICES,
        'condition_choices': Cartridge.CONDITION_CHOICES,
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
       
        locations_with_printers = Location.objects.filter(
            printer__is_active=True
        ).distinct()
        locations_data = [
            {'id': loc.id, 'name': loc.name}
            for loc in locations_with_printers
        ]
    else:
        
        locations = Location.objects.filter(is_active=True)
        locations_data = [
            {'id': loc.id, 'name': loc.name}
            for loc in locations
        ]
    
    return JsonResponse({'locations': locations_data})


@login_required
def search_cartridge_models(request):
    """API для поиска моделей картриджей"""
    query = request.GET.get('q', '')
    
    if query:
        models = CartridgeModel.objects.filter(
            Q(name__icontains=query) | 
            Q(manufacturer__icontains=query)
            
        ).order_by('manufacturer', 'name')[:20]  # Ограничиваем результаты
    else:
        models = CartridgeModel.objects.all().order_by('manufacturer', 'name')[:20]
    
    models_data = [
        {
            'id': model.id,
            'name': f"{model.manufacturer} {model.name}",
            'manufacturer': model.manufacturer,
            'model_name': model.name,
            'max_refills': model.max_refills
        }
        for model in models
    ]
    
    return JsonResponse({'models': models_data})


from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
@require_POST
def update_cartridge_condition(request, pk):
    """AJAX обновление состояния картриджа"""
    try:
        cartridge = get_object_or_404(Cartridge, pk=pk)
        new_condition = request.POST.get('condition')
        
        if new_condition in dict(Cartridge.CONDITION_CHOICES).keys():
            cartridge.condition = new_condition
            cartridge.save()
            
            # Логируем операцию изменения состояния
            Operation.objects.create(
                operation_type='transfer',
                cartridge=cartridge,
                from_location=cartridge.current_location,
                to_location=cartridge.current_location,
                user=request.user,
                reason=f'Изменено состояние на: {cartridge.get_condition_display()}',
                notes=f'Изменено через дашборд пользователем {request.user.username}'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Состояние изменено на: {cartridge.get_condition_display()}',
                'condition': cartridge.condition,
                'condition_display': cartridge.get_condition_display(),
                'badge_class': get_condition_badge_class(cartridge.condition)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Некорректное состояние'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def get_condition_badge_class(condition):
    """Возвращает CSS класс для бейджа состояния"""
    badge_classes = {
        'new': 'bg-success',
        'working': 'bg-primary',
        'refilled': 'bg-info',
        'needs_repair': 'bg-warning'
    }
    return badge_classes.get(condition, 'bg-secondary')



from django.views.decorators.http import require_POST

@login_required
@require_POST
def bulk_send_to_service(request):
    """Массовая отправка картриджей на заправку"""
    try:
        # Находим все картриджи, требующие ремонта
        cartridges_to_service = Cartridge.objects.filter(
            condition='needs_repair',
            current_status__in=['in_stock', 'installed']  # Только те, что на складе или установлены
        )
        
        count = 0
        errors = []
        
        # Находим локацию сервисного центра
        service_center = Location.objects.filter(type='service', is_active=True).first()
        if not service_center:
            return JsonResponse({
                'success': False,
                'error': 'Не найден активный сервисный центр'
            })
        
        for cartridge in cartridges_to_service:
            try:
                # Сохраняем текущую локацию
                from_location = cartridge.current_location
                
                # Обновляем статус картриджа
                cartridge.current_status = 'at_service'
                cartridge.current_location = service_center
                cartridge.save()
                
                # Создаём операцию
                Operation.objects.create(
                    operation_type='issue_service',
                    cartridge=cartridge,
                    from_location=from_location,
                    to_location=service_center,
                    user=request.user,
                    reason='Массовая отправка на заправку',
                    notes='Картридж требует ремонта, отправлен автоматически'
                )
                
                count += 1
                
            except Exception as e:
                errors.append(f"{cartridge.serial_number}: {str(e)}")
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'Успешно отправлено {count} картриджей на заправку',
            'count': count,
            'errors': errors if errors else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def send_to_service(request, pk):
    """Отправка одного картриджа на заправку"""
    try:
        cartridge = get_object_or_404(Cartridge, pk=pk)
        
        # Проверяем, можно ли отправить на заправку
        if cartridge.current_status == 'disposed':
            return JsonResponse({
                'success': False,
                'error': 'Нельзя отправить списанный картридж'
            })
        
        if cartridge.current_status == 'at_service':
            return JsonResponse({
                'success': False,
                'error': 'Картридж уже на заправке'
            })
        
        # Находим локацию сервисного центра
        service_center = Location.objects.filter(type='service', is_active=True).first()
        if not service_center:
            return JsonResponse({
                'success': False,
                'error': 'Не найден активный сервисный центр'
            })
        
        # Сохраняем текущую локацию
        from_location = cartridge.current_location
        
        # Обновляем статус картриджа
        cartridge.current_status = 'at_service'
        cartridge.current_location = service_center
        cartridge.save()
        
        # Создаём операцию
        Operation.objects.create(
            operation_type='issue_service',
            cartridge=cartridge,
            from_location=from_location,
            to_location=service_center,
            user=request.user,
            reason='Отправка на заправку',
            notes=f'Картридж отправлен на ремонт/заправку. Состояние: {cartridge.get_condition_display()}'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Картридж {cartridge.serial_number} отправлен на заправку',
            'status': cartridge.current_status,
            'status_display': cartridge.get_current_status_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


from django.shortcuts import render
from .models import Cartridge

def print_attention_report(request):
    """
    Печать отчёта по картриджам, требующим внимания
    (нуждаются в ремонте или превысили лимит заправок)
    """
    # Получаем те же картриджи, что и для дашборда
    attention_consumables = Cartridge.objects.filter(
        Q(condition='needs_repair') | 
        Q(refill_count__gt=F('model__max_refills'))
    ).select_related('model', 'installed_in_printer', 'current_location')  # Изменено здесь
    
    # Разделяем на две категории для отчёта
    needs_repair = attention_consumables.filter(condition='needs_repair')
    max_refills = attention_consumables.filter(refill_count__gt=F('model__max_refills'))
    
    context = {
        'needs_repair': needs_repair,
        'max_refills': max_refills,
        'total_count': attention_consumables.count(),
        'report_date': timezone.now().strftime('%d.%m.%Y %H:%M'),
    }
    
    return render(request, 'reports/attention_report.html', context)