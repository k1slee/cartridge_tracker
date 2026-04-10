from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cartridges', '0006_printer_is_inkjet_printer_printer_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartridge',
            name='marked_with_marker',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Помечен маркером'),
        ),
    ]

