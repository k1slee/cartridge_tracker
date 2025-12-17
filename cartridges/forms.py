from django import forms
from .models import Cartridge, Operation, CartridgeModel, Printer

class CartridgeForm(forms.ModelForm):
    class Meta:
        model = Cartridge
        fields = [
            'serial_number', 'consumable_type', 'model', 'current_location',
            'condition', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_serial_number'}),
            'consumable_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_consumable_type'}),
            'model': forms.Select(attrs={'class': 'form-control', 'id': 'id_model'}),
            'current_location': forms.Select(attrs={'class': 'form-control', 'id': 'id_current_location'}),
            'condition': forms.Select(attrs={'class': 'form-control', 'id': 'id_condition'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['model'].queryset = CartridgeModel.objects.all().order_by('manufacturer', 'name')

class OperationForm(forms.ModelForm):
    class Meta:
        model = Operation
        fields = ['operation_type', 'cartridge', 'from_location', 'to_location', 'printer', 'reason', 'notes']
        widgets = {
            'operation_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_operation_type'}),
            'cartridge': forms.Select(attrs={'class': 'form-control'}),
            'from_location': forms.Select(attrs={'class': 'form-control', 'id': 'id_from_location'}),
            'to_location': forms.Select(attrs={'class': 'form-control', 'id': 'id_to_location'}),
            'printer': forms.Select(attrs={'class': 'form-control', 'id': 'id_printer'}),
            'reason': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cartridge'].queryset = Cartridge.objects.exclude(current_status='disposed')
        self.fields['printer'].queryset = Printer.objects.filter(is_active=True)
        
        
        if 'to_location' in self.initial:
            location_id = self.initial['to_location']
            if location_id:
                self.fields['printer'].queryset = Printer.objects.filter(
                    location_id=location_id, 
                    is_active=True
                )

class PrinterForm(forms.ModelForm):
    class Meta:
        model = Printer
        fields = [
            'name', 'model', 'serial_number', 'printer_type', 'is_inkjet',
            'location', 'installation_date', 'is_active', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'printer_type': forms.Select(attrs={'class': 'form-control'}),
            'is_inkjet': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'location': forms.Select(attrs={'class': 'form-control'}),
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
       
        if self.instance and self.instance.printer_type == 'inkjet':
            self.fields['is_inkjet'].initial = True


class CartridgeConditionForm(forms.ModelForm):
    """Изменение статуса картриджа"""
    class Meta:
        model = Cartridge
        fields = ['condition']
        widgets = {
            'condition' : forms.Select(attrs={'class': 'form-control form-control-sm'}),
        }