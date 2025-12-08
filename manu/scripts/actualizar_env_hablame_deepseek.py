#!/usr/bin/env python
"""
Script para actualizar el archivo .env con las configuraciones de Hablame y Deepseek.
Lee el .env actual y agrega/actualiza las variables necesarias.
"""
import os
import re
from pathlib import Path

# Ruta del archivo .env
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'

# Configuraciones a agregar/actualizar
CONFIGURACIONES = {
    # Deepseek
    'DEEPSEEK_API_KEY': 'sk-f0ba5a27ac694372aa63ee974237a9b2',
    
    # Hablame - Credenciales principales
    'HABLAME_ACCOUNT': '10013855',
    'HABLAME_APIKEY': '4wnE24MumCFKoAcS89rkT3AiEhBMhK',
    'HABLAME_TOKEN': '5a70e03fde3f87b01f4488c7366e6515',
    
    # Hablame - URLs
    'HABLAME_SMS_URL': 'https://api103.hablame.co/api/sms/v3/send/priority',
    'HABLAME_SMS_REPORT_URL': 'https://api103.hablame.co/api/sms/v3/report/',
    'HABLAME_TTS_URL': 'https://api103.hablame.co/api/callblasting/v1/callblasting/tts_text',
    'HABLAME_TTS_STATUS_URL': 'https://api103.hablame.co/api/callblasting/v1/callblasting/status/',
    
    # Hablame - Configuraciones opcionales
    'HABLAME_SMS_SERVICE_CODE': '890202',
    'HABLAME_TTS_VOICE': 'es-US-natural-3',
    'HABLAME_MAX_INTENTOS': '3',
    'HABLAME_TIEMPO_ESPERA': '5',
}


def leer_env_actual():
    """Lee el archivo .env actual y retorna su contenido como lista de líneas"""
    if not ENV_FILE.exists():
        print(f"⚠️  El archivo .env no existe en {ENV_FILE}")
        print(f"📝 Se creará un nuevo archivo .env")
        return []
    
    try:
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            return f.readlines()
    except Exception as e:
        print(f"❌ Error leyendo .env: {e}")
        return []


def actualizar_env():
    """Actualiza el archivo .env con las nuevas configuraciones"""
    lineas = leer_env_actual()
    
    # Crear un diccionario con las variables existentes
    variables_existentes = {}
    lineas_nuevas = []
    seccion_actual = None
    
    # Procesar líneas existentes
    for linea in lineas:
        linea = linea.rstrip('\n\r')
        
        # Detectar secciones (comentarios que empiezan con #)
        if linea.strip().startswith('#') and ('DEEPSEEK' in linea.upper() or 'HABLAME' in linea.upper()):
            # Mantener comentarios de sección
            lineas_nuevas.append(linea)
            continue
        
        # Detectar variables
        if '=' in linea and not linea.strip().startswith('#'):
            partes = linea.split('=', 1)
            if len(partes) == 2:
                clave = partes[0].strip()
                valor = partes[1].strip()
                
                # Si es una variable que vamos a actualizar, la marcamos
                if clave in CONFIGURACIONES:
                    variables_existentes[clave] = True
                    # No agregamos esta línea, la reemplazaremos
                    continue
        
        # Mantener líneas que no son variables a actualizar
        lineas_nuevas.append(linea)
    
    # Agregar sección de Deepseek si no existe
    tiene_deepseek = any('DEEPSEEK' in k for k in variables_existentes)
    tiene_seccion_deepseek = any('# DEEPSEEK' in l.upper() or '# DEEPSEEK API' in l.upper() for l in lineas_nuevas)
    
    # Verificar si DEEPSEEK_API_KEY ya existe en las líneas
    tiene_deepseek_key = any('DEEPSEEK_API_KEY=' in l for l in lineas_nuevas)
    
    if not tiene_seccion_deepseek and not tiene_deepseek_key:
        lineas_nuevas.append('')
        lineas_nuevas.append('# ============================================')
        lineas_nuevas.append('# DEEPSEEK API (Para consultas inteligentes)')
        lineas_nuevas.append('# ============================================')
    
    # Agregar/actualizar variables de Deepseek
    if 'DEEPSEEK_API_KEY' not in variables_existentes and not tiene_deepseek_key:
        lineas_nuevas.append(f'DEEPSEEK_API_KEY={CONFIGURACIONES["DEEPSEEK_API_KEY"]}')
    else:
        # Buscar y reemplazar la línea existente
        encontrado = False
        for i, linea in enumerate(lineas_nuevas):
            if linea.strip().startswith('DEEPSEEK_API_KEY='):
                lineas_nuevas[i] = f'DEEPSEEK_API_KEY={CONFIGURACIONES["DEEPSEEK_API_KEY"]}'
                encontrado = True
                break
        if not encontrado and 'DEEPSEEK_API_KEY' not in variables_existentes:
            # Si no se encontró pero debería estar, agregarlo
            lineas_nuevas.append(f'DEEPSEEK_API_KEY={CONFIGURACIONES["DEEPSEEK_API_KEY"]}')
    
    # Agregar sección de Hablame si no existe
    tiene_hablame = any('HABLAME' in k for k in variables_existentes)
    tiene_seccion_hablame = any('# HABLAME' in l.upper() or '# HABLAME API' in l.upper() for l in lineas_nuevas)
    tiene_hablame_vars = any('HABLAME_ACCOUNT=' in l or 'HABLAME_APIKEY=' in l for l in lineas_nuevas)
    
    if not tiene_seccion_hablame and not tiene_hablame_vars:
        lineas_nuevas.append('')
        lineas_nuevas.append('# ============================================')
        lineas_nuevas.append('# HABLAME API (SMS y Llamadas)')
        lineas_nuevas.append('# ============================================')
    
    # Agregar/actualizar variables de Hablame
    for clave, valor in CONFIGURACIONES.items():
        if clave == 'DEEPSEEK_API_KEY':
            continue  # Ya lo procesamos arriba
        
        # Verificar si la variable ya existe en las líneas
        tiene_var = any(l.strip().startswith(f'{clave}=') for l in lineas_nuevas)
        
        if clave not in variables_existentes and not tiene_var:
            lineas_nuevas.append(f'{clave}={valor}')
        else:
            # Buscar y reemplazar la línea existente
            encontrado = False
            for i, linea in enumerate(lineas_nuevas):
                if linea.strip().startswith(f'{clave}='):
                    lineas_nuevas[i] = f'{clave}={valor}'
                    encontrado = True
                    break
            if not encontrado and clave not in variables_existentes:
                # Si no se encontró pero debería estar, agregarlo
                lineas_nuevas.append(f'{clave}={valor}')
    
    # Escribir el archivo actualizado
    try:
        # Crear backup
        if ENV_FILE.exists():
            backup_file = BASE_DIR / '.env.backup'
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                with open(backup_file, 'w', encoding='utf-8') as bf:
                    bf.write(f.read())
            print(f"✅ Backup creado: {backup_file}")
        
        # Escribir archivo actualizado
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lineas_nuevas))
            if lineas_nuevas and not lineas_nuevas[-1].endswith('\n'):
                f.write('\n')
        
        print(f"✅ Archivo .env actualizado exitosamente: {ENV_FILE}")
        print(f"\n📋 Variables agregadas/actualizadas:")
        print(f"   - DEEPSEEK_API_KEY")
        print(f"   - HABLAME_ACCOUNT")
        print(f"   - HABLAME_APIKEY")
        print(f"   - HABLAME_TOKEN")
        print(f"   - HABLAME_SMS_URL")
        print(f"   - HABLAME_SMS_REPORT_URL")
        print(f"   - HABLAME_TTS_URL")
        print(f"   - HABLAME_TTS_STATUS_URL")
        print(f"   - HABLAME_SMS_SERVICE_CODE")
        print(f"   - HABLAME_TTS_VOICE")
        print(f"   - HABLAME_MAX_INTENTOS")
        print(f"   - HABLAME_TIEMPO_ESPERA")
        print(f"\n⚠️  Recuerda reiniciar el servidor Django para que tome los nuevos valores.")
        
    except Exception as e:
        print(f"❌ Error escribiendo .env: {e}")
        return False
    
    return True


if __name__ == '__main__':
    print("🔧 Actualizando archivo .env con configuraciones de Hablame y Deepseek...")
    print(f"📁 Archivo: {ENV_FILE}\n")
    
    if actualizar_env():
        print("\n✅ Proceso completado exitosamente")
    else:
        print("\n❌ Error en el proceso")
        exit(1)

