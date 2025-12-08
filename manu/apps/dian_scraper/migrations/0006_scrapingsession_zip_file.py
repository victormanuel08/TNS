# Generated migration for ScrapingSession.zip_file

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dian_scraper', '0005_descargatemporaldianzip'),
    ]

    operations = [
        migrations.AddField(
            model_name='scrapingsession',
            name='zip_file',
            field=models.FileField(blank=True, help_text='ZIP permanente con todos los archivos de la sesión', null=True, upload_to='dian_exports/'),
        ),
    ]

