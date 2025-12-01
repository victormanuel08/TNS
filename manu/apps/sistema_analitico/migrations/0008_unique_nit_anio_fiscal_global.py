# Generated manually to change unique_together constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sistema_analitico', '0007_alter_empresaservidor_configuracion_and_more'),
    ]

    operations = [
        # Eliminar el constraint antiguo (servidor, nit, anio_fiscal)
        migrations.AlterUniqueTogether(
            name='empresaservidor',
            unique_together=set(),
        ),
        # Agregar el nuevo constraint (nit, anio_fiscal) - único globalmente
        migrations.AlterUniqueTogether(
            name='empresaservidor',
            unique_together={('nit', 'anio_fiscal')},
        ),
        # Agregar índices para mejorar performance
        migrations.AddIndex(
            model_name='empresaservidor',
            index=models.Index(fields=['nit', 'anio_fiscal'], name='sistema_an_nit_anio_idx'),
        ),
        migrations.AddIndex(
            model_name='empresaservidor',
            index=models.Index(fields=['servidor', 'nit'], name='sistema_an_servidor_nit_idx'),
        ),
    ]

