from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sistema_analitico', '0004_apikeycliente'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuarioempresa',
            name='preferred_template',
            field=models.CharField(
                choices=[
                    ('app', 'Aplicación Pro'),
                    ('restaurant', 'Restaurante / POS'),
                    ('retail', 'Retail / Autopago'),
                    ('pos', 'Punto de venta'),
                    ('pro', 'Vista profesional'),
                    ('autopago', 'Kiosco Autopago'),
                ],
                default='app',
                max_length=20,
            ),
        ),
    ]
