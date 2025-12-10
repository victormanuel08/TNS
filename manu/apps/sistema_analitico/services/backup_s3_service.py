"""
Servicio para gestionar backups de bases de datos Firebird a S3.
"""
import os
import subprocess
import logging
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.db.models import Q

from ..models import (
    EmpresaServidor, ConfiguracionS3, BackupS3
)

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    BotoConfig = None
    logger.warning("boto3 no está instalado. Los backups a S3 no funcionarán.")


class BackupS3Service:
    """
    Servicio para realizar backups de bases de datos Firebird a S3.
    """
    
    def __init__(self, configuracion_s3: ConfiguracionS3):
        """
        Inicializa el servicio con una configuración S3.
        
        Args:
            configuracion_s3: Configuración S3 a utilizar
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 no está instalado. Instala con: pip install boto3")
        
        self.config = configuracion_s3
        
        # Configurar cliente S3
        s3_kwargs = {
            'aws_access_key_id': configuracion_s3.access_key_id,
            'aws_secret_access_key': configuracion_s3.secret_access_key,
            'region_name': configuracion_s3.region,
        }
        
        if configuracion_s3.endpoint_url:
            # Para servicios S3-compatibles (como Contabo, MinIO), usar path-style
            endpoint_url = configuracion_s3.endpoint_url
            s3_kwargs['endpoint_url'] = endpoint_url
            
            # Force path-style para servicios S3-compatibles (no AWS)
            # Path-style: https://s3.contabo.com/bucket-name/key
            # Virtual-hosted: https://bucket-name.s3.contabo.com/key
            if BotoConfig:
                # Para Contabo, usar path-style explícitamente
                s3_config = BotoConfig(
                    signature_version='s3v4',
                    s3={
                        'addressing_style': 'path'  # Forzar path-style para Contabo
                    },
                    # También configurar retries y timeouts
                    retries={
                        'max_attempts': 3,
                        'mode': 'standard'
                    },
                    # Timeouts para evitar bloqueos indefinidos
                    connect_timeout=30,  # 30 segundos para conectar
                    read_timeout=300,    # 5 minutos para leer (upload de archivos grandes)
                    max_pool_connections=10
                )
                s3_kwargs['config'] = s3_config
                logger.info(f"Configurando S3 con endpoint: {endpoint_url}, path-style: True")
                logger.debug(f"Config S3: {s3_config}")
            else:
                logger.warning("BotoConfig no disponible, puede que path-style no funcione correctamente")
        
        try:
            self.s3_client = boto3.client('s3', **s3_kwargs)
            self.bucket_name = configuracion_s3.bucket_name
            
            # Verificar que el bucket existe y es accesible
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"Cliente S3 creado exitosamente. Bucket: {self.bucket_name} (verificado)")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code == '404':
                    logger.warning(f"⚠️ Bucket '{self.bucket_name}' no existe. Asegúrate de crearlo en Contabo.")
                elif error_code == '403':
                    logger.warning(f"⚠️ Sin permisos para acceder al bucket '{self.bucket_name}'. Verifica las credenciales.")
                else:
                    logger.warning(f"⚠️ Error verificando bucket '{self.bucket_name}': {error_code}")
                logger.info(f"Cliente S3 creado. Bucket: {self.bucket_name} (no verificado)")
        except Exception as e:
            logger.error(f"Error creando cliente S3: {e}", exc_info=True)
            raise
    
    def obtener_ruta_s3(self, empresa: EmpresaServidor, nombre_archivo: str) -> str:
        """
        Genera la ruta S3 para un backup según la estructura:
        {server_name}/{nit_normalizado}/{anio_fiscal}/backups/{nombre_archivo}
        
        Args:
            empresa: Empresa para la cual se genera la ruta
            nombre_archivo: Nombre del archivo de backup
            
        Returns:
            Ruta completa en S3
        """
        # Normalizar nombre del servidor (sin espacios, caracteres especiales)
        server_name = empresa.servidor.nombre.replace(' ', '_').replace('/', '_').replace('\\', '_')
        return f"{server_name}/{empresa.nit_normalizado}/{empresa.anio_fiscal}/backups/{nombre_archivo}"
    
    def _normalizar_nombre_archivo(self, nombre: str) -> str:
        """
        Normaliza un nombre de archivo para S3 (sin caracteres especiales).
        
        Args:
            nombre: Nombre original
            
        Returns:
            Nombre normalizado
        """
        # Reemplazar caracteres problemáticos
        nombre = nombre.replace('/', '_').replace('\\', '_').replace(':', '_')
        nombre = nombre.replace('*', '_').replace('?', '_').replace('"', '_')
        nombre = nombre.replace('<', '_').replace('>', '_').replace('|', '_')
        return nombre.strip()
    
    def registrar_backup_en_log(self, empresa: EmpresaServidor, exito: bool, peso_bytes: Optional[int] = None, 
                                 nombre_archivo: Optional[str] = None, error: Optional[str] = None) -> bool:
        """
        Registra un backup en el archivo de log de la empresa.
        El archivo se llama {razon_social}.txt y está en {server_name}/{nit_normalizado}/
        
        Si el archivo no existe, lo crea con un header. Luego apendee cada backup como una línea de log.
        
        Estructura:
            {server_name}/{nit_normalizado}/{razon_social}.txt
        
        Formato del log:
            [YYYY-MM-DD HH:MM:SS] [ÉXITO/ERROR] Backup: {nombre_archivo} | Peso: {peso_mb} MB | {error si falló}
        
        Args:
            empresa: Empresa para la cual registrar el backup
            exito: True si el backup fue exitoso, False si falló
            peso_bytes: Tamaño del archivo de backup en bytes (si fue exitoso)
            nombre_archivo: Nombre del archivo de backup
            error: Mensaje de error si falló
            
        Returns:
            True si se registró exitosamente, False si hubo algún error
        """
        try:
            from datetime import datetime
            
            server_name = empresa.servidor.nombre.replace(' ', '_').replace('/', '_').replace('\\', '_')
            prefix_empresa = f"{server_name}/{empresa.nit_normalizado}/"
            
            # Normalizar razón social para el nombre del archivo
            razon_social = getattr(empresa, 'razon_social', None) or empresa.nombre or f"Empresa_{empresa.codigo}"
            razon_social_normalizada = self._normalizar_nombre_archivo(razon_social)
            nombre_txt = f"{razon_social_normalizada}.txt"
            ruta_s3_txt = f"{prefix_empresa}{nombre_txt}"
            
            # Verificar si el archivo ya existe
            contenido_existente = ""
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=ruta_s3_txt)
                contenido_existente = response['Body'].read().decode('utf-8')
            except ClientError as e:
                if e.response.get('Error', {}).get('Code') != 'NoSuchKey':
                    # Error diferente a "no existe", registrar y continuar
                    logger.warning(f"Error leyendo archivo de log existente: {e}")
                # Si no existe, contenido_existente queda vacío y crearemos el header
            
            # Preparar la línea de log
            fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            estado = "ÉXITO" if exito else "ERROR"
            
            # Formatear peso
            if peso_bytes and peso_bytes > 0:
                peso_mb = peso_bytes / (1024 * 1024)
                peso_str = f"{peso_mb:.2f} MB"
            else:
                peso_str = "N/A"
            
            # Construir línea de log
            linea_log = f"[{fecha_hora}] [{estado}]"
            if nombre_archivo:
                linea_log += f" Backup: {nombre_archivo}"
            linea_log += f" | Peso: {peso_str}"
            if not exito and error:
                linea_log += f" | Error: {error}"
            linea_log += "\n"
            
            # Si el archivo no existe, crear header primero
            if not contenido_existente:
                header = f"=== LOG DE BACKUPS - {razon_social} ===\n"
                header += f"NIT: {empresa.nit_normalizado}\n"
                if getattr(empresa, 'nit', None):
                    header += f"NIT original: {empresa.nit}\n"
                if getattr(empresa, 'representante_legal', None):
                    header += f"Representante Legal: {empresa.representante_legal}\n"
                header += f"Código: {empresa.codigo}\n"
                header += f"Servidor: {empresa.servidor.nombre}\n"
                header += "=" * 50 + "\n\n"
                contenido_existente = header
            
            # Agregar la nueva línea de log
            nuevo_contenido = contenido_existente + linea_log
            
            # Subir el archivo actualizado
            contenido_bytes = nuevo_contenido.encode('utf-8')
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=ruta_s3_txt,
                Body=contenido_bytes,
                ContentType='text/plain; charset=utf-8'
            )
            
            logger.debug(f"Backup registrado en log: {ruta_s3_txt}")
            return True
                    
        except Exception as e:
            logger.error(f"Error registrando backup en log para {empresa.nombre}: {e}", exc_info=True)
            return False
    
    def obtener_tamano_actual_gb(self, empresa: EmpresaServidor) -> float:
        """
        Calcula el tamaño total en GB usado en S3 por una empresa (por servidor y NIT normalizado),
        considerando TODOS los años fiscales, backups y demás carpetas/documentos.
        
        Args:
            empresa: EmpresaServidor específica (se usa servidor.nombre + nit_normalizado)
            
        Returns:
            Tamaño total en GB
        """
        try:
            # Estructura: {server_name}/{nit_normalizado}/{anio_fiscal}/backups/{archivo}
            # El límite es por empresa (servidor + NIT normalizado), sumando:
            # - Todos los años fiscales
            # - Todos los backups
            # - Cualquier otra carpeta/documento bajo ese prefijo.
            server_name = empresa.servidor.nombre.replace(' ', '_').replace('/', '_').replace('\\', '_')
            prefix = f"{server_name}/{empresa.nit_normalizado}/"
            total_bytes = 0
            
            # Para path-style, el bucket debe ir en la ruta, no en el dominio
            # Usar list_objects_v2 con el bucket en el parámetro
            logger.debug(f"Listando objetos en S3 con prefix: {prefix}, bucket: {self.bucket_name}")
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_bytes += obj['Size']
            
            return round(total_bytes / (1024 * 1024 * 1024), 2)
        except Exception as e:
            logger.error(f"Error calculando tamaño de backups para {empresa.nombre}: {e}")
            return 0.0
    
    def crear_backup_firebird(
        self,
        empresa: EmpresaServidor,
        gbak_path: Optional[str] = None,
        usuario: str = "SYSDBA",
        contrasena: str = "masterkey"
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Crea un backup de la base de datos Firebird de una empresa.
        
        Args:
            empresa: Empresa para la cual crear el backup
            gbak_path: Ruta al ejecutable gbak.exe
            usuario: Usuario de Firebird
            contrasena: Contraseña de Firebird
            
        Returns:
            Tupla (éxito, ruta_archivo_temporal, tamano_bytes)
        """
        if not empresa.ruta_base:
            logger.error(f"Empresa {empresa.nombre} no tiene ruta_base configurada")
            return False, None, None

        # Construir ruta completa considerando servidor remoto
        # Si ruta_base es una ruta local, usarla directamente
        # Si el servidor es remoto, usar formato host:ruta_base para gbak
        servidor_host = empresa.servidor.host
        ruta_completa = empresa.ruta_base
        
        # Si el servidor no es localhost/127.0.0.1, construir ruta remota
        if servidor_host and servidor_host not in ['localhost', '127.0.0.1', '::1']:
            # Para backup remoto, gbak usa formato: host:ruta_base
            # IMPORTANTE: Para rutas de Windows con caracteres especiales (como Ñ), 
            # usar formato TCP/IP con puerto explícito para evitar errores de transliteración
            puerto_firebird = empresa.servidor.puerto or 3050
            ruta_base_encoded = empresa.ruta_base
            
            # Si la ruta contiene caracteres especiales, usar formato host/port:ruta
            # Esto ayuda a gbak en Linux a manejar mejor los caracteres especiales de Windows
            # Verificar si hay caracteres no ASCII en la ruta
            tiene_caracteres_especiales = any(ord(c) > 127 for c in ruta_base_encoded)
            
            if tiene_caracteres_especiales:
                # Usar formato con puerto explícito para mejor compatibilidad con caracteres especiales
                ruta_completa = f"{servidor_host}/{puerto_firebird}:{ruta_base_encoded}"
                logger.info(f"🌐 Usando ruta remota con puerto explícito (caracteres especiales detectados): {ruta_completa}")
            else:
                # Formato estándar para rutas sin caracteres especiales
                ruta_completa = f"{servidor_host}:{ruta_base_encoded}"
                logger.info(f"🌐 Usando ruta remota para backup: {ruta_completa}")
            
            logger.info(f"   Verificando conectividad con {servidor_host}...")
            
            # Verificar conectividad básica (puerto 3050) antes de intentar backup
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)  # 5 segundos timeout
                resultado_ping = sock.connect_ex((servidor_host, 3050))
                sock.close()
                
                if resultado_ping != 0:
                    logger.warning(f"⚠️ No se puede conectar al puerto 3050 de {servidor_host}")
                    logger.warning(f"   Esto puede causar que el backup falle")
                    logger.warning(f"   Verificar: Firebird corriendo, firewall, VPN")
                else:
                    logger.info(f"✅ Conexión al puerto 3050 de {servidor_host} exitosa")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo verificar conectividad con {servidor_host}: {e}")
        else:
            # Verificar que existe localmente
            if not os.path.exists(empresa.ruta_base):
                logger.error(f"Archivo de base de datos no existe localmente: {empresa.ruta_base}")
                return False, None, None
        # Determinar ruta de gbak de forma portable:
        # - Si se pasa explícitamente, usarla.
        # - Si no, leer FIREBIRD_GBAK_PATH de settings.
        # - Si no existe, usar una ruta por defecto según el SO.
        if gbak_path is None:
            try:
                from django.conf import settings
                gbak_path = getattr(settings, "FIREBIRD_GBAK_PATH", None)
            except Exception:
                gbak_path = None

        if gbak_path is None:
            # Buscar gbak.exe en ubicaciones comunes
            if os.name == "nt":
                # Rutas comunes de Firebird en Windows
                # Orden: primero (x86) porque es más común en sistemas de 64 bits
                posibles_rutas = [
                    r"C:\Program Files (x86)\Firebird\Firebird_2_5\bin\gbak.exe",  # Más común
                    r"C:\Program Files (x86)\Firebird\Firebird_3_0\bin\gbak.exe",
                    r"C:\Program Files\Firebird\Firebird_2_5\bin\gbak.exe",
                    r"C:\Program Files\Firebird\Firebird_3_0\bin\gbak.exe",
                    r"C:\Program Files\Firebird\Firebird_4_0\bin\gbak.exe",
                    r"C:\Firebird\bin\gbak.exe",
                ]
                gbak_path = None
                logger.info(f"Buscando gbak.exe en {len(posibles_rutas)} ubicaciones...")
                for ruta in posibles_rutas:
                    existe = os.path.exists(ruta)
                    logger.debug(f"Verificando: {ruta} - Existe: {existe}")
                    if existe:
                        gbak_path = ruta
                        logger.info(f"✅ Encontrado gbak.exe en: {ruta}")
                        break
                
                if gbak_path is None:
                    # Intentar buscar en PATH
                    import shutil
                    logger.info("Buscando gbak.exe en PATH del sistema...")
                    gbak_path = shutil.which("gbak.exe")
                    if gbak_path:
                        logger.info(f"✅ Encontrado gbak.exe en PATH: {gbak_path}")
                
                if gbak_path is None:
                    logger.error("❌ No se encontró gbak.exe en ninguna ubicación.")
                    logger.error(f"Ubicaciones verificadas: {posibles_rutas}")
                    logger.error("Configure FIREBIRD_GBAK_PATH en settings.py o instale Firebird.")
                    return False, None, None
                
                # Verificar una vez más que existe antes de continuar
                if not os.path.exists(gbak_path):
                    logger.error(f"❌ gbak.exe no existe en la ruta encontrada: {gbak_path}")
                    return False, None, None
            else:
                # En Linux/Ubuntu (VPS): gbak normalmente está en el PATH después de instalar Firebird
                # Si no está, puede estar en /usr/bin/gbak o /usr/local/bin/gbak
                import shutil
                gbak_path = shutil.which("gbak")
                
                # Si no está en PATH, buscar en ubicaciones comunes de Ubuntu
                # IMPORTANTE: Buscar primero Firebird 2.5 (compatible con las bases de datos .GDB)
                if not gbak_path:
                    posibles_rutas_linux = [
                        "/opt/firebird2.5/opt/firebird/bin/gbak",  # Ruta real después de extraer buildroot.tar.gz
                        "/opt/firebird2.5/bin/gbak",  # Ruta alternativa
                        "/usr/local/bin/gbak",  # Symlink común (apunta a Firebird 2.5)
                        "/usr/local/firebird2.5/bin/gbak",  # Otra ruta común
                        "/home/victus/firebird2.5/bin/gbak",  # Ruta en home del usuario
                        "/usr/bin/gbak",  # Firebird 3.0 (fallback, puede causar problemas de compatibilidad)
                        "/opt/firebird/bin/gbak",
                    ]
                    for ruta in posibles_rutas_linux:
                        if os.path.exists(ruta):
                            gbak_path = ruta
                            logger.info(f"Encontrado gbak en: {ruta}")
                            break
                
                if not gbak_path:
                    logger.error(
                        "No se encontró gbak en el sistema. "
                        "IMPORTANTE: Las bases de datos son Firebird 2.5, se recomienda usar gbak 2.5.\n"
                        "Opciones:\n"
                        "1. Descargar Firebird 2.5 manualmente desde https://firebirdsql.org/en/downloads/\n"
                        "   Extraer en /opt/firebird2.5/ y crear symlink: sudo ln -s /opt/firebird2.5/bin/gbak /usr/local/bin/gbak\n"
                        "2. O instalar Firebird 3.0 (puede causar problemas al restaurar en servidores 2.5):\n"
                        "   sudo apt-get install firebird3.0-utils\n"
                        "3. O configurar FIREBIRD_GBAK_PATH en settings.py con la ruta completa a gbak 2.5"
                    )
                    return False, None, None
                
                logger.info(f"Usando gbak desde: {gbak_path}")
        
        # Generar nombre de archivo temporal (siempre local, no en servidor remoto)
        fecha_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        nombre_archivo = f"backup_{fecha_str}.fbk"
        
        # Crear directorio temporal local si no existe
        import tempfile
        temp_dir = tempfile.gettempdir()
        ruta_temporal = os.path.join(temp_dir, f"backup_{empresa.nit_normalizado}_{nombre_archivo}")
        
        try:
            # Ejecutar gbak
            # Si es servidor remoto, usar formato host:ruta_base
            # Si es local, usar ruta_base directamente
            comando = [
                gbak_path,
                '-user', usuario,
                '-pass', contrasena,
                '-b',  # Backup
                '-v',  # Verbose
                ruta_completa,  # Usa ruta_completa (puede ser host:ruta o ruta local)
                ruta_temporal  # Siempre guardar localmente
            ]
            
            logger.info(f"Ejecutando gbak desde: {gbak_path}")
            logger.info(f"Origen: {ruta_completa}")
            logger.info(f"Destino: {ruta_temporal}")
            logger.info(f"⏳ Iniciando backup... Esto puede tardar varios minutos dependiendo del tamaño de la base de datos.")
            
            # Verificar que gbak.exe existe antes de ejecutar
            if not os.path.exists(gbak_path):
                logger.error(f"gbak.exe no existe en: {gbak_path}")
                return False, None, None
            
            # Usar Popen para capturar salida en tiempo real y mostrar progreso
            import time
            import threading
            
            # Redirigir stdout y stderr a archivos temporales para evitar bloqueos de buffer
            stdout_file = os.path.join(temp_dir, f"gbak_stdout_{empresa.nit_normalizado}_{int(time.time())}.log")
            stderr_file = os.path.join(temp_dir, f"gbak_stderr_{empresa.nit_normalizado}_{int(time.time())}.log")
            
            stdout_fd = open(stdout_file, 'w')
            stderr_fd = open(stderr_file, 'w')
            
            # Configurar variables de entorno para manejar caracteres especiales
            env = os.environ.copy()
            # Establecer codificación UTF-8 para manejar caracteres especiales de Windows (como Ñ)
            env['LC_ALL'] = 'C.UTF-8'
            env['LANG'] = 'C.UTF-8'
            
            proceso = subprocess.Popen(
                comando,
                stdout=stdout_fd,
                stderr=stderr_fd,
                text=True,
                env=env  # Pasar variables de entorno
            )
            
            # Monitorear el proceso y mostrar progreso cada 30 segundos
            inicio = time.time()
            ultimo_log = inicio
            ultimo_tamano = 0
            ultimo_progreso = inicio  # Inicializar desde el inicio
            timeout_total = 1800  # 30 minutos máximo
            timeout_sin_progreso = 300  # 5 minutos sin crecimiento del archivo = colgado
            timeout_archivo_no_existe = 120  # 2 minutos sin que exista el archivo = bloqueado
            
            logger.info(f"⏳ Monitoreando proceso gbak (PID: {proceso.pid})...")
            logger.info(f"   Timeouts: total={timeout_total//60}min, sin_progreso={timeout_sin_progreso//60}min, archivo_no_existe={timeout_archivo_no_existe}s")
            
            while True:
                # Verificar si terminó
                if proceso.poll() is not None:
                    codigo_salida = proceso.returncode
                    logger.info(f"✅ Proceso gbak terminó con código: {codigo_salida}")
                    break
                
                tiempo_transcurrido = time.time() - inicio
                
                # Verificar timeout total
                if tiempo_transcurrido > timeout_total:
                    proceso.kill()
                    logger.error(f"⏱️ Timeout total: El backup tardó más de {timeout_total//60} minutos")
                    logger.error(f"   Proceso gbak (PID: {proceso.pid}) fue terminado forzosamente")
                    return False, None, None
                
                # Verificar si el archivo está creciendo (detectar procesos colgados)
                tamano_actual = 0
                archivo_existe = os.path.exists(ruta_temporal)
                
                if archivo_existe:
                    tamano_actual = os.path.getsize(ruta_temporal)
                    if tamano_actual > ultimo_tamano:
                        # El archivo está creciendo, resetear contador
                        ultimo_tamano = tamano_actual
                        ultimo_progreso = time.time()
                        logger.debug(f"📈 Archivo creciendo: {tamano_actual} bytes (+{tamano_actual - ultimo_tamano} bytes)")
                    else:
                        # El archivo no está creciendo
                        tiempo_sin_progreso = time.time() - ultimo_progreso
                        if tiempo_sin_progreso > timeout_sin_progreso:
                            proceso.kill()
                            logger.error(f"⏱️ Timeout sin progreso: El archivo no ha crecido en {timeout_sin_progreso//60} minutos. Proceso probablemente colgado.")
                            logger.error(f"   Tamaño del archivo: {tamano_actual} bytes (sin cambios)")
                            logger.error(f"   Proceso gbak (PID: {proceso.pid}) fue terminado forzosamente")
                            logger.error(f"   Tiempo transcurrido: {int(tiempo_transcurrido//60)} minutos")
                            return False, None, None
                else:
                    # Archivo no existe aún - verificar si el proceso está bloqueado
                    tiempo_sin_archivo = tiempo_transcurrido
                    # Mostrar advertencia cada 30 segundos si el archivo no existe
                    if tiempo_sin_archivo > 30 and int(tiempo_sin_archivo) % 30 < 2:
                        logger.warning(f"⚠️ Archivo de backup aún no existe después de {int(tiempo_sin_archivo)} segundos...")
                        logger.warning(f"   Ruta esperada: {ruta_temporal}")
                        logger.warning(f"   Si el archivo no aparece en {timeout_archivo_no_existe} segundos, el proceso será terminado")
                    
                    if tiempo_sin_archivo > timeout_archivo_no_existe:
                        proceso.kill()
                        logger.error(f"⏱️ Timeout: El archivo de backup no se creó después de {timeout_archivo_no_existe} segundos ({timeout_archivo_no_existe//60} minutos)")
                        logger.error(f"   Ruta esperada: {ruta_temporal}")
                        logger.error(f"   Proceso gbak (PID: {proceso.pid}) probablemente bloqueado esperando respuesta de Firebird")
                        logger.error(f"   Empresa: {empresa.nombre}")
                        if hasattr(empresa, 'servidor') and empresa.servidor:
                            logger.error(f"   Servidor: {empresa.servidor.host}:{empresa.servidor.puerto}")
                        logger.error(f"   Base de datos: {empresa.ruta_base}")
                        logger.error(f"   Proceso fue terminado forzosamente")
                        
                        # Intentar leer stderr para ver si hay algún error
                        try:
                            if os.path.exists(stderr_file):
                                with open(stderr_file, 'r') as f:
                                    stderr_content = f.read()
                                    if stderr_content:
                                        logger.error(f"   Últimos errores de gbak:\n{stderr_content[-500:]}")  # Últimos 500 caracteres
                        except Exception as e:
                            logger.warning(f"   No se pudo leer stderr: {e}")
                        
                        return False, None, None
                
                # Mostrar progreso cada 30 segundos (SIEMPRE mostrar el tamaño actual)
                if time.time() - ultimo_log >= 30:
                    minutos = int(tiempo_transcurrido // 60)
                    segundos = int(tiempo_transcurrido % 60)
                    tamano_mb = tamano_actual / (1024 * 1024)  # Mostrar tamaño ACTUAL, no el último registrado
                    logger.info(f"⏳ Backup en progreso... Tiempo: {minutos}m {segundos}s, Tamaño: {tamano_mb:.2f} MB")
                    ultimo_log = time.time()
                
                time.sleep(2)  # Verificar cada 2 segundos
            
            # Esperar a que termine el proceso (ya está siendo monitoreado en el while)
            proceso.wait()
            stdout_fd.close()
            stderr_fd.close()
            
            # Leer stdout y stderr de los archivos
            stdout = ""
            if os.path.exists(stdout_file):
                with open(stdout_file, 'r') as f:
                    stdout = f.read()
                try:
                    os.remove(stdout_file)
                except:
                    pass
            
            stderr = ""
            if os.path.exists(stderr_file):
                with open(stderr_file, 'r') as f:
                    stderr = f.read()
                try:
                    os.remove(stderr_file)
                except:
                    pass
            
            resultado = type('obj', (object,), {
                'returncode': proceso.returncode,
                'stdout': stdout,
                'stderr': stderr
            })()
            
            tiempo_total = time.time() - inicio
            logger.info(f"✅ gbak terminó en {int(tiempo_total//60)}m {int(tiempo_total%60)}s")
            
            if resultado.returncode != 0:
                error_msg = resultado.stderr.strip() if resultado.stderr else "Error desconocido"
                logger.error(f"❌ Error ejecutando gbak para {empresa.nombre}:")
                logger.error(f"   Código de salida: {resultado.returncode}")
                logger.error(f"   Error: {error_msg}")
                
                # Detectar errores comunes y dar sugerencias
                if "Unable to complete network request" in error_msg or "Error reading data from the connection" in error_msg:
                    logger.error(f"   🔍 Problema de conexión detectado:")
                    logger.error(f"      - Verificar que el servidor {ruta_completa.split(':')[0]} esté accesible")
                    logger.error(f"      - Verificar que Firebird esté corriendo en el servidor remoto")
                    logger.error(f"      - Verificar firewall y VPN")
                elif "timeout" in error_msg.lower():
                    logger.error(f"   🔍 Timeout detectado: El backup tardó demasiado")
                
                return False, None, None
            
            # Verificar que el archivo se creó
            if not os.path.exists(ruta_temporal):
                logger.error(f"El archivo de backup no se creó: {ruta_temporal}")
                return False, None, None
            
            tamano = os.path.getsize(ruta_temporal)
            return True, ruta_temporal, tamano
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ Timeout al crear backup para {empresa.nombre} (más de 30 minutos)")
            logger.error(f"   Esto puede indicar:")
            logger.error(f"   - Problemas de conexión de red")
            logger.error(f"   - Base de datos muy grande")
            logger.error(f"   - Servidor remoto no responde")
            return False, None, None
        except Exception as e:
            logger.error(f"Error creando backup para {empresa.nombre}: {e}", exc_info=True)
            return False, None, None
    
    def subir_backup_a_s3(
        self,
        empresa: EmpresaServidor,
        ruta_archivo_local: str,
        nombre_archivo: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Sube un archivo de backup a S3.
        
        Args:
            empresa: Empresa para la cual se sube el backup
            ruta_archivo_local: Ruta local del archivo de backup
            nombre_archivo: Nombre del archivo en S3
            
        Returns:
            Tupla (éxito, ruta_s3)
        """
        if not os.path.exists(ruta_archivo_local):
            logger.error(f"Archivo no existe: {ruta_archivo_local}")
            return False, None
        
        try:
            ruta_s3 = self.obtener_ruta_s3(empresa, nombre_archivo)
            
            # Subir archivo
            # Nota: Contabo S3 puede no soportar ServerSideEncryption, así que lo removemos
            # Si necesitas encriptación, hazlo localmente antes de subir
            # No pasar ExtraArgs si está vacío (igual que en el test que funciona)
            
            tamano_archivo = os.path.getsize(ruta_archivo_local)
            tamano_mb = tamano_archivo / (1024 * 1024)
            
            logger.info(f"☁️ Iniciando subida a S3: bucket={self.bucket_name}, key={ruta_s3}")
            logger.info(f"   Archivo local: {ruta_archivo_local} ({tamano_mb:.2f} MB / {tamano_archivo} bytes)")
            logger.info(f"   Timeout configurado: connect=30s, read=300s (5 min)")
            
            # Usar upload_file sin ExtraArgs (igual que el test exitoso)
            # El timeout está configurado en BotoConfig (connect_timeout=30, read_timeout=300)
            inicio_upload = time.time()
            self.s3_client.upload_file(
                ruta_archivo_local,
                self.bucket_name,
                ruta_s3
            )
            tiempo_upload = time.time() - inicio_upload
            
            logger.info(f"✅ Backup subido exitosamente a S3: {ruta_s3} (tiempo: {tiempo_upload:.2f}s, velocidad: {tamano_mb/tiempo_upload:.2f} MB/s)")
            
            # Registrar backup exitoso en el log
            try:
                peso_bytes = os.path.getsize(ruta_archivo_local)
                self.registrar_backup_en_log(
                    empresa=empresa,
                    exito=True,
                    peso_bytes=peso_bytes,
                    nombre_archivo=nombre_archivo
                )
            except Exception as e:
                # No fallar el backup si falla el registro en el log
                logger.warning(f"No se pudo registrar backup en log para {empresa.nombre}: {e}")
            
            return True, ruta_s3
            
        except ClientError as e:
            logger.error(f"Error de AWS S3 al subir backup: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Error inesperado al subir backup: {e}", exc_info=True)
            return False, None
    
    def eliminar_backup_s3(self, ruta_s3: str) -> bool:
        """
        Elimina un archivo de backup de S3.
        
        Args:
            ruta_s3: Ruta completa del archivo en S3
            
        Returns:
            True si se eliminó exitosamente
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=ruta_s3)
            logger.info(f"Backup eliminado de S3: {ruta_s3}")
            return True
        except Exception as e:
            logger.error(f"Error eliminando backup de S3: {e}")
            return False
    
    def necesita_backup_anio_anterior(self, empresa: EmpresaServidor) -> Tuple[bool, Optional[int]]:
        """
        Verifica si una empresa de año fiscal anterior necesita backup.
        
        Args:
            empresa: Empresa para la cual verificar
            
        Returns:
            Tupla (necesita_backup, anio_fiscal) si necesita, (False, None) si no
        """
        from datetime import timedelta
        
        anio_fiscal_actual = empresa.anio_fiscal
        fecha_actual = timezone.now()
        treinta_dias_atras = fecha_actual - timedelta(days=30)
        
        # Solo verificar empresas de años fiscales anteriores
        if empresa.anio_fiscal >= date.today().year:
            return False, None
        
        # Buscar el backup más reciente de este año fiscal
        backup_mas_reciente = BackupS3.objects.filter(
            empresa_servidor=empresa,
            anio_fiscal=empresa.anio_fiscal,
            estado='completado'
        ).order_by('-fecha_backup').first()
        
        # Si no hay backup o tiene más de 30 días, necesita backup
        if not backup_mas_reciente:
            return True, empresa.anio_fiscal
        
        if backup_mas_reciente.fecha_backup.replace(tzinfo=None) < treinta_dias_atras.replace(tzinfo=None):
            logger.info(f"Backup de año fiscal {empresa.anio_fiscal} tiene más de 30 días, necesita reemplazo")
            return True, empresa.anio_fiscal
        
        return False, None
    
    def aplicar_politica_retencion(self, empresa: EmpresaServidor) -> Dict[str, int]:
        """
        Aplica la política de retención de backups:
        - Años fiscales anteriores: 1 backup por año (reemplazar si tiene más de 30 días)
        - Año fiscal actual: máximo 3 backups (3 días)
        
        Args:
            empresa: Empresa para la cual aplicar la política
            
        Returns:
            Diccionario con estadísticas de eliminación
        """
        from datetime import timedelta
        
        anio_actual = date.today().year
        anio_fiscal_actual = empresa.anio_fiscal
        fecha_actual = timezone.now()
        treinta_dias_atras = fecha_actual - timedelta(days=30)
        
        # Obtener todos los backups de la empresa
        backups = BackupS3.objects.filter(
            empresa_servidor=empresa,
            estado='completado'
        ).order_by('anio_fiscal', '-fecha_backup')
        
        eliminados = 0
        conservados = 0
        
        # Agrupar por año fiscal
        backups_por_anio = {}
        for backup in backups:
            anio = backup.anio_fiscal
            if anio not in backups_por_anio:
                backups_por_anio[anio] = []
            backups_por_anio[anio].append(backup)
        
        # Aplicar política
        for anio, backups_anio in backups_por_anio.items():
            if anio < anio_fiscal_actual:
                # Años anteriores: conservar solo el más reciente
                # Si el más reciente tiene más de 1 mes, eliminarlo para que se cree uno nuevo
                backups_ordenados = sorted(backups_anio, key=lambda b: b.fecha_backup, reverse=True)
                backup_mas_reciente = backups_ordenados[0] if backups_anio else None
                
                # Eliminar todos excepto el más reciente
                for backup in backups_ordenados[1:]:
                    if self.eliminar_backup_s3(backup.ruta_s3):
                        backup.delete()
                        eliminados += 1
                
                # Si el backup más reciente tiene más de 30 días, eliminarlo para mantenerlo fresco
                if backup_mas_reciente:
                    if backup_mas_reciente.fecha_backup.replace(tzinfo=None) < treinta_dias_atras.replace(tzinfo=None):
                        logger.info(f"Backup de año fiscal {anio} tiene más de 30 días ({backup_mas_reciente.fecha_backup}), eliminando para mantenerlo fresco")
                        if self.eliminar_backup_s3(backup_mas_reciente.ruta_s3):
                            backup_mas_reciente.delete()
                            eliminados += 1
                        conservados = 0  # Se reemplazará en el próximo backup
                    else:
                        conservados = 1  # Conservar el más reciente
                else:
                    conservados = 0
                    
            elif anio == anio_fiscal_actual:
                # Año fiscal actual: conservar máximo 3 backups (3 días)
                backups_ordenados = sorted(backups_anio, key=lambda b: b.fecha_backup, reverse=True)
                for backup in backups_ordenados[3:]:  # Eliminar todos después del 3ro
                    if self.eliminar_backup_s3(backup.ruta_s3):
                        backup.delete()
                        eliminados += 1
                conservados += min(3, len(backups_ordenados))
        
        return {
            'eliminados': eliminados,
            'conservados': conservados
        }
    
    def verificar_limite_espacio(self, empresa: EmpresaServidor) -> Tuple[bool, float, float]:
        """
        Verifica si la empresa ha excedido su límite de espacio.
        
        Args:
            empresa: Empresa para verificar
            
        Returns:
            Tupla (excede_limite, tamano_actual_gb, limite_gb)
        """
        try:
            tamano_actual = self.obtener_tamano_actual_gb(empresa)
        except Exception as e:
            # Si no se puede calcular el tamaño (problema de conexión S3), 
            # asumimos 0 y continuamos (no bloqueamos el backup)
            logger.warning(f"No se pudo calcular tamaño actual para {empresa.nombre}: {e}. Continuando con backup.")
            tamano_actual = 0.0

        # El límite es por empresa (NIT normalizado), no por año fiscal individual.
        # Tomamos el mayor límite configurado entre todos los años fiscales de ese NIT,
        # para evitar que un año con límite más bajo bloquee al resto.
        from ..models import EmpresaServidor as EmpresaServidorModel
        empresas_mismo_nit = EmpresaServidorModel.objects.filter(
            nit_normalizado=empresa.nit_normalizado
        )
        if empresas_mismo_nit.exists():
            limite = max(e.limite_espacio_gb for e in empresas_mismo_nit)
        else:
            limite = empresa.limite_espacio_gb
        
        excede = tamano_actual >= limite
        
        return excede, tamano_actual, limite
    
    def realizar_backup_completo(
        self,
        empresa: EmpresaServidor,
        gbak_path: Optional[str] = None,  # None = buscar automáticamente
        usuario: str = "SYSDBA",
        contrasena: str = "masterkey"
    ) -> Tuple[bool, Optional[BackupS3], Optional[str]]:
        """
        Realiza un backup completo: crea el backup local, lo sube a S3 y aplica política de retención.
        
        Args:
            empresa: Empresa para la cual realizar el backup
            gbak_path: Ruta al ejecutable gbak.exe
            usuario: Usuario de Firebird
            contrasena: Contraseña de Firebird
            
        Returns:
            Tupla (éxito, objeto_backup_s3, mensaje_error)
        """
        # Verificar límite de espacio
        excede, tamano_actual, limite = self.verificar_limite_espacio(empresa)
        if excede:
            mensaje = f"Límite de espacio excedido: {tamano_actual:.2f} GB / {limite} GB"
            logger.warning(f"Backup no realizado para {empresa.nombre}: {mensaje}")
            return False, None, mensaje
        
        # Crear backup local
        logger.info(f"📦 Creando backup local con gbak para {empresa.nombre}...")
        exito, ruta_local, tamano = self.crear_backup_firebird(empresa, gbak_path, usuario, contrasena)
        if not exito:
            error_msg = "Error al crear backup local"
            logger.error(f"❌ {error_msg} para {empresa.nombre}")
            # Registrar error en log
            try:
                self.registrar_backup_en_log(
                    empresa=empresa,
                    exito=False,
                    error=error_msg
                )
            except Exception as e:
                logger.warning(f"No se pudo registrar error en log: {e}")
            return False, None, error_msg
        
        tamano_mb = tamano / (1024 * 1024) if tamano else 0
        logger.info(f"✅ Backup local creado: {os.path.basename(ruta_local)} ({tamano_mb:.2f} MB)")
        
        nombre_archivo = os.path.basename(ruta_local)
        
        try:
            # Subir a S3
            logger.info(f"☁️ Subiendo backup a S3 (Contabo) para {empresa.nombre}...")
            exito_upload, ruta_s3 = self.subir_backup_a_s3(empresa, ruta_local, nombre_archivo)
            if not exito_upload:
                error_msg = "Error al subir backup a S3"
                logger.error(f"❌ {error_msg} para {empresa.nombre}")
                # Registrar error en log
                try:
                    self.registrar_backup_en_log(
                        empresa=empresa,
                        exito=False,
                        peso_bytes=tamano,
                        nombre_archivo=nombre_archivo,
                        error=error_msg
                    )
                except Exception as e:
                    logger.warning(f"No se pudo registrar error en log: {e}")
                # Limpiar archivo local
                if os.path.exists(ruta_local):
                    os.remove(ruta_local)
                return False, None, error_msg
            
            logger.info(f"✅ Backup subido exitosamente a S3: {ruta_s3}")
            
            # Registrar en BD
            logger.info(f"💾 Creando registro en base de datos para {empresa.nombre}...")
            backup_s3 = BackupS3.objects.create(
                empresa_servidor=empresa,
                configuracion_s3=self.config,
                ruta_s3=ruta_s3,
                nombre_archivo=nombre_archivo,
                tamano_bytes=tamano,
                fecha_backup=timezone.now(),
                anio_fiscal=empresa.anio_fiscal,
                estado='completado'
            )
            logger.info(f"✅ Registro creado: BackupS3 ID {backup_s3.id}")
            
            # Aplicar política de retención
            logger.info(f"🧹 Aplicando política de retención para {empresa.nombre}...")
            stats = self.aplicar_politica_retencion(empresa)
            logger.info(f"✅ Política aplicada: {stats['eliminados']} eliminados, {stats['conservados']} conservados")
            
            # Limpiar archivo local
            if os.path.exists(ruta_local):
                os.remove(ruta_local)
            
            logger.info(f"🎉 Backup completado exitosamente para {empresa.nombre}: {ruta_s3}")
            return True, backup_s3, None
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error en backup completo para {empresa.nombre}: {error_msg}", exc_info=True)
            # Registrar error en log
            try:
                self.registrar_backup_en_log(
                    empresa=empresa,
                    exito=False,
                    error=error_msg
                )
            except Exception as log_error:
                logger.warning(f"No se pudo registrar error en log: {log_error}")
            # Limpiar archivo local
            if os.path.exists(ruta_local):
                os.remove(ruta_local)
            return False, None, error_msg
    
    def listar_backups(self, empresa: EmpresaServidor) -> List[Dict]:
        """
        Lista todos los backups de una empresa en S3.
        
        Args:
            empresa: Empresa para la cual listar backups
            
        Returns:
            Lista de diccionarios con información de backups
        """
        backups = BackupS3.objects.filter(
            empresa_servidor=empresa
        ).order_by('-fecha_backup')
        
        return [
            {
                'id': b.id,
                'nombre_archivo': b.nombre_archivo,
                'ruta_s3': b.ruta_s3,
                'tamano_mb': b.tamano_mb,
                'tamano_gb': b.tamano_gb,
                'fecha_backup': b.fecha_backup.isoformat(),
                'anio_fiscal': b.anio_fiscal,
                'estado': b.estado,
            }
            for b in backups
        ]
    
    def eliminar_backup(self, backup_id: int) -> bool:
        """
        Elimina un backup específico de S3 y de la BD.
        
        Args:
            backup_id: ID del backup a eliminar
            
        Returns:
            True si se eliminó exitosamente
        """
        try:
            backup = BackupS3.objects.get(id=backup_id)
            ruta_s3 = backup.ruta_s3
            
            if self.eliminar_backup_s3(ruta_s3):
                backup.delete()
                return True
            return False
        except BackupS3.DoesNotExist:
            logger.error(f"Backup con ID {backup_id} no existe")
            return False
        except Exception as e:
            logger.error(f"Error eliminando backup: {e}")
            return False

