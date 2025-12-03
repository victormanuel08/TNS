"""
Servicio para gestionar backups de bases de datos Firebird a S3.
"""
import os
import subprocess
import logging
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
                    }
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
        {nit_normalizado}/{anio_fiscal}/backups/{nombre_archivo}
        
        Args:
            empresa: Empresa para la cual se genera la ruta
            nombre_archivo: Nombre del archivo de backup
            
        Returns:
            Ruta completa en S3
        """
        return f"{empresa.nit_normalizado}/{empresa.anio_fiscal}/backups/{nombre_archivo}"
    
    def obtener_tamano_actual_gb(self, empresa: EmpresaServidor) -> float:
        """
        Calcula el tamaño total en GB usado en S3 por una empresa (por NIT normalizado),
        considerando TODOS los años fiscales, backups y demás carpetas/documentos.
        
        Args:
            empresa: Cualquier EmpresaServidor de ese NIT (se usa nit_normalizado)
            
        Returns:
            Tamaño total en GB
        """
        try:
            # Un solo bucket global para todas las empresas.
            # El límite es por empresa (NIT normalizado), sumando:
            # - Todos los años fiscales
            # - Todos los backups
            # - Cualquier otra carpeta/documento bajo ese prefijo.
            prefix = f"{empresa.nit_normalizado}/"
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
            ruta_completa = f"{servidor_host}:{empresa.ruta_base}"
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
            proceso = subprocess.Popen(
                comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitorear el proceso y mostrar progreso cada 30 segundos
            inicio = time.time()
            ultimo_log = inicio
            timeout_total = 1800  # 30 minutos máximo
            
            while True:
                # Verificar si terminó
                if proceso.poll() is not None:
                    break
                
                # Verificar timeout
                tiempo_transcurrido = time.time() - inicio
                if tiempo_transcurrido > timeout_total:
                    proceso.kill()
                    logger.error(f"⏱️ Timeout: El backup tardó más de {timeout_total//60} minutos")
                    return False, None, None
                
                # Mostrar progreso cada 30 segundos
                if time.time() - ultimo_log >= 30:
                    minutos = int(tiempo_transcurrido // 60)
                    segundos = int(tiempo_transcurrido % 60)
                    logger.info(f"⏳ Backup en progreso... Tiempo transcurrido: {minutos}m {segundos}s")
                    ultimo_log = time.time()
                
                time.sleep(2)  # Verificar cada 2 segundos
            
            # Obtener resultado
            stdout, stderr = proceso.communicate()
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
            extra_args = {}
            # Solo agregar metadata si es necesario
            # extra_args['Metadata'] = {'empresa': empresa.nombre}
            
            logger.debug(f"Subiendo archivo a S3: bucket={self.bucket_name}, key={ruta_s3}")
            self.s3_client.upload_file(
                ruta_archivo_local,
                self.bucket_name,
                ruta_s3,
                ExtraArgs=extra_args if extra_args else None
            )
            
            logger.info(f"Backup subido exitosamente a S3: {ruta_s3}")
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
            logger.error(f"❌ Error al crear backup local para {empresa.nombre}")
            return False, None, "Error al crear backup local"
        
        tamano_mb = tamano / (1024 * 1024) if tamano else 0
        logger.info(f"✅ Backup local creado: {os.path.basename(ruta_local)} ({tamano_mb:.2f} MB)")
        
        nombre_archivo = os.path.basename(ruta_local)
        
        try:
            # Subir a S3
            logger.info(f"☁️ Subiendo backup a S3 (Contabo) para {empresa.nombre}...")
            exito_upload, ruta_s3 = self.subir_backup_a_s3(empresa, ruta_local, nombre_archivo)
            if not exito_upload:
                logger.error(f"❌ Error al subir backup a S3 para {empresa.nombre}")
                # Limpiar archivo local
                if os.path.exists(ruta_local):
                    os.remove(ruta_local)
                return False, None, "Error al subir backup a S3"
            
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
            logger.error(f"Error en backup completo para {empresa.nombre}: {e}", exc_info=True)
            # Limpiar archivo local
            if os.path.exists(ruta_local):
                os.remove(ruta_local)
            return False, None, str(e)
    
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

