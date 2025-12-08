# Generated migration for DescargaTemporalDianZip

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone
from datetime import timedelta


class Migration(migrations.Migration):

    dependencies = [
        ('dian_scraper', '0004_scrapingrange_delete_scrapingcoverage'),
    ]

    operations = [
        migrations.CreateModel(
            name='DescargaTemporalDianZip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, help_text='Token único y seguro para la descarga', max_length=64, unique=True)),
                ('email', models.EmailField(help_text='Email del destinatario al que se envió el link', max_length=254)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('procesando', 'Procesando'), ('listo', 'Listo'), ('expirado', 'Expirado'), ('descargado', 'Descargado')], default='pendiente', help_text='Estado del proceso de generación del ZIP', max_length=20)),
                ('ruta_zip_temporal', models.CharField(blank=True, help_text='Ruta temporal del archivo ZIP generado', max_length=500, null=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_expiracion', models.DateTimeField(help_text='Fecha en que expira el link (1 día después de la creación)')),
                ('fecha_descarga', models.DateTimeField(blank=True, help_text='Fecha en que se descargó el archivo', null=True)),
                ('intentos_descarga', models.IntegerField(default=0, help_text='Número de veces que se ha intentado descargar')),
                ('session', models.ForeignKey(help_text='Sesión de scraping que generó el ZIP', on_delete=django.db.models.deletion.CASCADE, related_name='descargas_temporales', to='dian_scraper.scrapingsession')),
            ],
            options={
                'verbose_name': 'Descarga Temporal de ZIP DIAN',
                'verbose_name_plural': 'Descargas Temporales de ZIP DIAN',
                'db_table': 'descargas_temporales_dian_zip',
                'ordering': ['-fecha_creacion'],
            },
        ),
        migrations.AddIndex(
            model_name='descargatemporaldianzip',
            index=models.Index(fields=['token'], name='descargas_t_token_idx'),
        ),
        migrations.AddIndex(
            model_name='descargatemporaldianzip',
            index=models.Index(fields=['fecha_expiracion'], name='descargas_t_fecha_ex_idx'),
        ),
        migrations.AddIndex(
            model_name='descargatemporaldianzip',
            index=models.Index(fields=['estado'], name='descargas_t_estado_idx'),
        ),
    ]

