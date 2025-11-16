from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('sistema_analitico', '0005_usuarioempresa_preferred_template'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserTenantProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subdomain', models.CharField(max_length=50, unique=True)),
                ('preferred_template', models.CharField(choices=[('app', 'Aplicación Pro'), ('restaurant', 'Restaurante / POS'), ('retail', 'Retail / Autopago'), ('pos', 'Punto de venta'), ('pro', 'Vista profesional'), ('autopago', 'Kiosco Autopago')], default='app', max_length=20)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='tenant_profile', to='auth.user')),
            ],
            options={'db_table': 'user_tenant_profiles'},
        ),
    ]
