from django.urls import path
from . import views

app_name = 'cartridges'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    
    path('cartridges/', views.cartridge_list, name='cartridge_list'),
    path('cartridges/add/', views.cartridge_create, name='cartridge_create'),
    path('cartridges/<int:pk>/', views.cartridge_detail, name='cartridge_detail'),
    
    path('printers/', views.printer_list, name='printer_list'),
    path('printers/add/', views.printer_create, name='printer_create'),
    path('printers/<int:pk>/', views.printer_detail, name='printer_detail'),
    
   
    path('operations/add/', views.operation_create, name='operation_create'),
    path('operations/add/<int:cartridge_pk>/', views.operation_create, name='operation_create_for_cartridge'),
    path('api/cartridge/<int:cartridge_id>/', views.get_cartridge_info, name='cartridge_info'),
]