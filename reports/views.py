from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from cartridges.models import Cartridge, Operation, CartridgeModel, Location

@login_required
def reports_dashboard(request):
    """Дашборд с отчётами"""
    
    # Статистика по статусам
    status_stats = Cartridge.objects.values('current_status').annotate(
        count=Count('id')
    )
    
    # Статистика по моделям
    model_stats = CartridgeModel.objects.annotate(
        total=Count('cartridge'),
        in_stock=Count('cartridge', filter=Q(cartridge__current_status='in_stock')),
        installed=Count('cartridge', filter=Q(cartridge__current_status='installed'))
    )
    
    # Картриджи на заправке
    at_service = Cartridge.objects.filter(current_status='at_service').select_related('model', 'current_location')
    
    # Картриджи с превышением лимита заправок
    over_refilled = Cartridge.objects.filter(
        refill_count__gte=models.F('model__max_refills')
    ).select_related('model')
    
    context = {
        'status_stats': status_stats,
        'model_stats': model_stats,
        'at_service': at_service,
        'over_refilled': over_refilled,
    }
    return render(request, 'reports/dashboard.html', context)

@login_required
def stock_report(request):
    """Отчёт об остатках на складах"""
    from django.db.models import Count, Q
    
    locations = Location.objects.filter(is_active=True).annotate(
        total_cartridges=Count('cartridge', filter=Q(cartridge__current_status='in_stock'))
    )
    
    # Группировка по моделям для каждого склада
    stock_by_location = {}
    for location in locations:
        models_stats = CartridgeModel.objects.annotate(
            count=Count('cartridge', filter=Q(cartridge__current_location=location, cartridge__current_status='in_stock'))
        ).filter(count__gt=0)
        stock_by_location[location] = models_stats
    
    context = {
        'locations': locations,
        'stock_by_location': stock_by_location,
    }
    return render(request, 'reports/stock_report.html', context)

@login_required
def refill_report(request):
    """Отчёт по заправкам"""
    from django.db.models import Count
    from datetime import datetime, timedelta
    
    # Статистика по заправкам за последние 30 дней
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_refills = Operation.objects.filter(
        operation_type='receive_service',
        timestamp__gte=thirty_days_ago
    ).values('cartridge__model__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Топ картриджей по количеству заправок
    top_refilled = Cartridge.objects.filter(refill_count__gt=0).order_by('-refill_count')[:10]
    context = {
        'recent_refills': recent_refills,
        'top_refilled': top_refilled,
    }
    return render(request, 'reports/refill_report.html', context)