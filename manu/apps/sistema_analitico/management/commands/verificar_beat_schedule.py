#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comando para verificar el schedule de Celery Beat.

Muestra todas las tareas programadas configuradas en CELERY_BEAT_SCHEDULE.
"""

import os
import sys
import django
from django.core.management.base import BaseCommand

# Configurar Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

from django.conf import settings
from celery.schedules import crontab


class Command(BaseCommand):
    help = 'Verifica el schedule de Celery Beat configurado'

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write("Schedule de Celery Beat")
        self.stdout.write("=" * 70)
        self.stdout.write("")
        
        if not hasattr(settings, 'CELERY_BEAT_SCHEDULE') or not settings.CELERY_BEAT_SCHEDULE:
            self.stdout.write(self.style.WARNING("⚠️  No hay tareas programadas configuradas"))
            return
        
        schedule = settings.CELERY_BEAT_SCHEDULE
        
        self.stdout.write(f"📋 Total de tareas programadas: {len(schedule)}")
        self.stdout.write("")
        
        for nombre, config in schedule.items():
            self.stdout.write(f"📌 {nombre}")
            self.stdout.write(f"   Tarea: {config.get('task', 'N/A')}")
            
            schedule_obj = config.get('schedule')
            if schedule_obj:
                if isinstance(schedule_obj, crontab):
                    # Mostrar información del crontab
                    hora = schedule_obj.hour
                    minuto = schedule_obj.minute
                    dia_semana = schedule_obj.day_of_week
                    dia_mes = schedule_obj.day_of_month
                    mes = schedule_obj.month_of_year
                    
                    if hora == '*' and minuto == '*':
                        self.stdout.write(f"   Horario: Cada minuto")
                    elif hora == '*' and minuto != '*':
                        self.stdout.write(f"   Horario: Cada hora a los {minuto} minutos")
                    elif hora != '*' and minuto == '*':
                        self.stdout.write(f"   Horario: Cada minuto de la hora {hora}")
                    else:
                        hora_str = str(hora) if isinstance(hora, int) else ', '.join(map(str, hora)) if isinstance(hora, (list, tuple)) else hora
                        minuto_str = str(minuto) if isinstance(minuto, int) else ', '.join(map(str, minuto)) if isinstance(minuto, (list, tuple)) else minuto
                        self.stdout.write(f"   Horario: {hora_str}:{minuto_str:0>2} (formato 24h)")
                    
                    if dia_semana != '*':
                        self.stdout.write(f"   Día de semana: {dia_semana}")
                    if dia_mes != '*':
                        self.stdout.write(f"   Día del mes: {dia_mes}")
                    if mes != '*':
                        self.stdout.write(f"   Mes: {mes}")
                else:
                    self.stdout.write(f"   Horario: {schedule_obj}")
            else:
                self.stdout.write(f"   Horario: No configurado")
            
            if 'args' in config:
                self.stdout.write(f"   Argumentos: {config['args']}")
            if 'kwargs' in config:
                self.stdout.write(f"   Argumentos nombrados: {config['kwargs']}")
            
            self.stdout.write("")
        
        self.stdout.write("=" * 70)
        self.stdout.write("")
        self.stdout.write("💡 Para verificar que Celery Beat está corriendo:")
        self.stdout.write("   sudo systemctl status celerybeat.service")
        self.stdout.write("")
        self.stdout.write("💡 Para ver los logs de Celery Beat:")
        self.stdout.write("   sudo journalctl -u celerybeat.service -f")
        self.stdout.write("")
        self.stdout.write("💡 Al iniciar Celery Beat, deberías ver en los logs:")
        self.stdout.write("   'beat: Starting...'")
        self.stdout.write("   Y luego las tareas programadas listadas")

