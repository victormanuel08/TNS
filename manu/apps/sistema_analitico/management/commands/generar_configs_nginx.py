#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comando para generar configuraciones de Nginx basadas en EmpresaDominio.

Lee automáticamente todas las configuraciones de Nginx existentes para extraer
los server_name y construir una lista de dominios a excluir. Luego genera
configuraciones solo para dominios de EmpresaDominio que no estén ya configurados.
"""

import os
import re
import sys
from pathlib import Path
from typing import Set, List, Dict
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.sistema_analitico.models import EmpresaDominio


class Command(BaseCommand):
    help = 'Genera configuraciones de Nginx para dominios de EmpresaDominio, excluyendo dominios ya configurados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra lo que haría sin crear archivos',
        )
        parser.add_argument(
            '--nginx-dir',
            type=str,
            default='/etc/nginx',
            help='Directorio base de Nginx (default: /etc/nginx)',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='/etc/nginx/sites-available',
            help='Directorio donde crear las configuraciones (default: /etc/nginx/sites-available)',
        )
        parser.add_argument(
            '--frontend-port',
            type=int,
            default=3001,
            help='Puerto del frontend Nuxt (default: 3001)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        nginx_dir = Path(options['nginx_dir'])
        output_dir = Path(options['output_dir'])
        frontend_port = options['frontend_port']

        self.stdout.write("=" * 80)
        self.stdout.write("Generador de Configuraciones de Nginx")
        self.stdout.write("=" * 80)
        self.stdout.write("")

        # Paso 1: Leer configuraciones existentes de Nginx
        self.stdout.write("📖 Paso 1: Leyendo configuraciones existentes de Nginx...")
        mapeo_nginx = self._leer_dominios_nginx(nginx_dir)
        dominios_excluidos = set(mapeo_nginx.keys())
        
        self.stdout.write(f"   ✅ Encontrados {len(dominios_excluidos)} dominios ya configurados:")
        for dominio in sorted(dominios_excluidos):
            archivo = mapeo_nginx[dominio]['archivo']
            self.stdout.write(f"      - {dominio} → {archivo.name}")
        self.stdout.write("")

        # Paso 2: Leer dominios de EmpresaDominio
        self.stdout.write("📋 Paso 2: Leyendo dominios de EmpresaDominio...")
        dominios_empresa = EmpresaDominio.objects.filter(activo=True).values_list('dominio', flat=True)
        dominios_empresa = set(dominios_empresa)
        
        self.stdout.write(f"   ✅ Encontrados {len(dominios_empresa)} dominios activos en BD:")
        for dominio in sorted(dominios_empresa):
            self.stdout.write(f"      - {dominio}")
        self.stdout.write("")

        # Paso 3: Identificar dominios que necesitan configuración o actualización
        dominios_a_configurar = []
        dominios_a_actualizar = []
        
        for dominio in dominios_empresa:
            if dominio in mapeo_nginx:
                # Dominio ya existe, verificar si necesita actualización
                info = mapeo_nginx[dominio]
                # Por ahora, marcamos para actualizar si el archivo parece ser del frontend
                if self._es_config_frontend(info['contenido'], frontend_port):
                    dominios_a_actualizar.append((dominio, info))
                else:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  {dominio} ya configurado en {info['archivo'].name} (no es frontend, se omite)"))
            else:
                # Dominio nuevo, necesita configuración
                dominios_a_configurar.append(dominio)
        
        if not dominios_a_configurar and not dominios_a_actualizar:
            self.stdout.write(self.style.SUCCESS("✅ Todos los dominios ya están configurados en Nginx"))
            return
        
        self.stdout.write(f"🔧 Paso 3: Análisis de dominios")
        if dominios_a_configurar:
            self.stdout.write(f"   📝 Nuevos dominios a configurar: {len(dominios_a_configurar)}")
            for dominio in sorted(dominios_a_configurar):
                self.stdout.write(f"      - {dominio}")
        if dominios_a_actualizar:
            self.stdout.write(f"   🔄 Dominios a actualizar: {len(dominios_a_actualizar)}")
            for dominio, info in dominios_a_actualizar:
                self.stdout.write(f"      - {dominio} → {info['archivo'].name}")
        self.stdout.write("")

        # Paso 4: Crear backups de archivos a modificar
        if dominios_a_actualizar and not dry_run:
            self.stdout.write("💾 Paso 4: Creando backups de archivos existentes...")
            backups_creados = self._crear_backups(dominios_a_actualizar, nginx_dir)
            for archivo_original, backup_path in backups_creados.items():
                self.stdout.write(self.style.SUCCESS(f"   ✅ Backup: {archivo_original.name} → {backup_path.name}"))
            self.stdout.write("")

        # Paso 5: Generar/actualizar configuraciones
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 MODO DRY-RUN: No se crearán/modificarán archivos"))
            self.stdout.write("")
        
        configuraciones_creadas = []
        configuraciones_actualizadas = []
        
        # Crear configuraciones nuevas
        for dominio in sorted(dominios_a_configurar):
            config_path = output_dir / f"ecommerce-{self._sanitize_filename(dominio)}"
            
            config_content = self._generar_config_nginx(dominio, frontend_port)
            
            if dry_run:
                self.stdout.write(f"   📝 Crearía: {config_path}")
                self.stdout.write(f"      Contenido:")
                for line in config_content.split('\n'):
                    self.stdout.write(f"         {line}")
            else:
                try:
                    # Crear archivo
                    with open(config_path, 'w', encoding='utf-8') as f:
                        f.write(config_content)
                    
                    # Crear enlace simbólico en sites-enabled
                    enabled_path = nginx_dir / 'sites-enabled' / config_path.name
                    if not enabled_path.exists():
                        os.symlink(config_path, enabled_path)
                    
                    configuraciones_creadas.append(dominio)
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Creado: {config_path.name}"))
                except PermissionError:
                    self.stdout.write(self.style.ERROR(f"   ❌ Error: Sin permisos para crear {config_path}"))
                    self.stdout.write(self.style.WARNING(f"      Ejecuta: sudo python manage.py generar_configs_nginx"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Error creando {config_path}: {e}"))
        
        # Actualizar configuraciones existentes
        for dominio, info in dominios_a_actualizar:
            archivo = info['archivo']
            
            if dry_run:
                self.stdout.write(f"   🔄 Actualizaría: {archivo.name}")
                self.stdout.write(f"      Agregaría/actualizaría configuración para {dominio}")
            else:
                try:
                    # Leer contenido actual
                    with open(archivo, 'r', encoding='utf-8') as f:
                        contenido_actual = f.read()
                    
                    # Actualizar o agregar configuración para este dominio
                    contenido_nuevo = self._actualizar_config_nginx(
                        contenido_actual, dominio, frontend_port
                    )
                    
                    # Escribir archivo actualizado
                    with open(archivo, 'w', encoding='utf-8') as f:
                        f.write(contenido_nuevo)
                    
                    configuraciones_actualizadas.append(dominio)
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Actualizado: {archivo.name} (dominio: {dominio})"))
                except PermissionError:
                    self.stdout.write(self.style.ERROR(f"   ❌ Error: Sin permisos para modificar {archivo}"))
                    self.stdout.write(self.style.WARNING(f"      Ejecuta: sudo python manage.py generar_configs_nginx"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Error actualizando {archivo}: {e}"))
        
        self.stdout.write("")

        # Paso 6: Verificar y recargar Nginx
        if (configuraciones_creadas or configuraciones_actualizadas) and not dry_run:
            self.stdout.write("🔍 Paso 6: Verificando configuración de Nginx...")
            import subprocess
            try:
                result = subprocess.run(
                    ['sudo', 'nginx', '-t'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    self.stdout.write(self.style.SUCCESS("   ✅ Configuración de Nginx válida"))
                    self.stdout.write("")
                    self.stdout.write(self.style.WARNING("   ⚠️  Para aplicar los cambios, ejecuta:"))
                    self.stdout.write("      sudo systemctl reload nginx")
                else:
                    self.stdout.write(self.style.ERROR("   ❌ Error en configuración de Nginx:"))
                    self.stdout.write(result.stderr)
            except FileNotFoundError:
                self.stdout.write(self.style.WARNING("   ⚠️  Comando 'nginx' no encontrado. Verifica manualmente."))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   ⚠️  No se pudo verificar Nginx: {e}"))

        self.stdout.write("")
        self.stdout.write("=" * 80)
        if dry_run:
            total = len(dominios_a_configurar) + len(dominios_a_actualizar)
            self.stdout.write(self.style.SUCCESS(f"✅ DRY-RUN completado. Se crearían {len(dominios_a_configurar)} configuraciones nuevas y se actualizarían {len(dominios_a_actualizar)} existentes"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Completado. {len(configuraciones_creadas)} configuraciones creadas, {len(configuraciones_actualizadas)} actualizadas"))
        self.stdout.write("=" * 80)

    def _es_config_frontend(self, contenido: str, frontend_port: int) -> bool:
        """
        Detecta si una configuración de Nginx es para el frontend Nuxt.
        Busca proxy_pass al puerto del frontend.
        """
        # Buscar proxy_pass al puerto del frontend
        pattern = rf'proxy_pass\s+http://localhost:{frontend_port}'
        return bool(re.search(pattern, contenido, re.IGNORECASE))

    def _crear_backups(self, dominios_a_actualizar: List, nginx_dir: Path) -> Dict:
        """
        Crea backups de archivos que se van a modificar.
        Retorna dict: {archivo_original: Path_backup}
        """
        backups = {}
        backup_dir = nginx_dir / 'sites-available' / '.backups'
        
        # Crear directorio de backups si no existe
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            self.stdout.write(self.style.WARNING(f"   ⚠️  No se pudo crear directorio de backups: {backup_dir}"))
            return backups
        
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for dominio, info in dominios_a_actualizar:
            archivo = info['archivo']
            backup_name = f"{archivo.stem}_{timestamp}.backup"
            backup_path = backup_dir / backup_name
            
            try:
                # Copiar archivo
                import shutil
                shutil.copy2(archivo, backup_path)
                backups[archivo] = backup_path
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   ⚠️  No se pudo crear backup de {archivo.name}: {e}"))
        
        return backups

    def _actualizar_config_nginx(self, contenido_actual: str, dominio: str, frontend_port: int) -> str:
        """
        Actualiza una configuración de Nginx existente para incluir/actualizar un dominio.
        Si el dominio ya está en server_name, lo mantiene. Si no, lo agrega.
        """
        # Verificar si el dominio ya está en algún server_name
        pattern = r'server_name\s+([^;]+);'
        matches = list(re.finditer(pattern, contenido_actual, re.IGNORECASE | re.MULTILINE))
        
        if not matches:
            # No hay server_name, agregar bloque completo
            nuevo_bloque = self._generar_config_nginx(dominio, frontend_port)
            return contenido_actual + "\n\n" + nuevo_bloque
        
        # Buscar si el dominio ya está en algún server_name
        dominio_encontrado = False
        for match in matches:
            server_names = match.group(1).strip().split()
            if dominio.lower() in [s.lower().strip('"\'') for s in server_names]:
                dominio_encontrado = True
                break
        
        if dominio_encontrado:
            # Dominio ya está configurado, no hacer nada
            return contenido_actual
        
        # Dominio no está, agregarlo al primer server_name encontrado
        # (asumiendo que es el bloque principal)
        primer_match = matches[0]
        server_names_actuales = primer_match.group(1).strip()
        
        # Agregar el nuevo dominio
        nuevo_server_names = f"{server_names_actuales} {dominio} www.{dominio}"
        nuevo_server_name_line = f"    server_name {nuevo_server_names};"
        
        # Reemplazar en el contenido
        contenido_nuevo = contenido_actual[:primer_match.start()] + \
                         nuevo_server_name_line + \
                         contenido_actual[primer_match.end():]
        
        return contenido_nuevo

    def _leer_dominios_nginx(self, nginx_dir: Path) -> Dict[str, Dict]:
        """
        Lee todas las configuraciones de Nginx y extrae los server_name.
        Retorna un dict: {dominio: {'archivo': Path, 'contenido': str, 'server_names': List}}
        """
        mapeo_dominios = {}  # dominio -> info del archivo
        sites_available = nginx_dir / 'sites-available'
        sites_enabled = nginx_dir / 'sites-enabled'
        
        # Leer de sites-available (más completo, evita duplicados)
        directorios_a_leer = []
        if sites_available.exists():
            directorios_a_leer.append(('available', sites_available))
        if sites_enabled.exists():
            directorios_a_leer.append(('enabled', sites_enabled))
        
        if not directorios_a_leer:
            self.stdout.write(self.style.WARNING(f"   ⚠️  No se encontró /etc/nginx/sites-available ni sites-enabled"))
            return mapeo_dominios
        
        for tipo, directorio in directorios_a_leer:
            for archivo in directorio.iterdir():
                if archivo.is_file() and not archivo.name.startswith('.'):
                    try:
                        with open(archivo, 'r', encoding='utf-8') as f:
                            contenido = f.read()
                        
                        # Extraer todos los server_name
                        server_names = self._extraer_server_names(contenido)
                        
                        # Mapear cada dominio al archivo
                        for dominio in server_names:
                            if dominio not in mapeo_dominios:
                                mapeo_dominios[dominio] = {
                                    'archivo': archivo,
                                    'tipo': tipo,
                                    'contenido': contenido,
                                    'server_names': server_names,
                                }
                    except (PermissionError, UnicodeDecodeError) as e:
                        # Ignorar archivos que no se pueden leer
                        continue
        
        return mapeo_dominios

    def _extraer_server_names(self, contenido: str) -> List[str]:
        """
        Extrae todos los server_name de un contenido de configuración de Nginx.
        Maneja múltiples server_name, wildcards, y regex.
        """
        dominios = []
        
        # Buscar todos los bloques server_name
        # Patrón: server_name dominio1 dominio2 dominio3;
        pattern = r'server_name\s+([^;]+);'
        matches = re.findall(pattern, contenido, re.IGNORECASE | re.MULTILINE)
        
        for match in matches:
            # Limpiar y dividir por espacios
            server_names = match.strip().split()
            
            for server_name in server_names:
                # Limpiar comillas
                server_name = server_name.strip('"\'')
                
                # Ignorar wildcards y regex (pero extraer el dominio base si es posible)
                if server_name == '_' or server_name == 'default_server':
                    # Catch-all, no agregar
                    continue
                elif '*' in server_name:
                    # Wildcard como *.eddeso.com
                    # Extraer el dominio base (eddeso.com)
                    dominio_base = server_name.replace('*.', '').replace('*', '')
                    if dominio_base and '.' in dominio_base:
                        dominios.append(dominio_base)
                elif server_name.startswith('~'):
                    # Regex, intentar extraer dominio si es posible
                    # Por ahora, ignorar regex complejos
                    continue
                elif '.' in server_name:
                    # Dominio normal
                    dominios.append(server_name.lower())
        
        return dominios

    def _sanitize_filename(self, dominio: str) -> str:
        """Convierte un dominio en un nombre de archivo seguro"""
        # Reemplazar caracteres no válidos
        nombre = dominio.replace('.', '_').replace('*', 'wildcard')
        # Limitar longitud
        if len(nombre) > 50:
            nombre = nombre[:50]
        return nombre

    def _generar_config_nginx(self, dominio: str, frontend_port: int) -> str:
        """Genera el contenido de configuración de Nginx para un dominio"""
        # Incluir www también
        www_dominio = f"www.{dominio}"
        
        config = f"""# Configuración generada automáticamente para {dominio}
# Generado por: python manage.py generar_configs_nginx
# NO EDITAR MANUALMENTE - Se regenerará automáticamente

server {{
    listen 80;
    server_name {dominio} {www_dominio};

    location / {{
        proxy_pass http://localhost:{frontend_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }}
}}
"""
        return config

