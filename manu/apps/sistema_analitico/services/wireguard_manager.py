# sistema_analitico/services/wireguard_manager.py
"""
Servicio para gestionar configuraciones de WireGuard.
Ejecuta comandos wg vía SSH en el servidor Linux remoto.
"""
import subprocess
import os
import secrets
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from django.conf import settings

try:
    import paramiko
except ImportError:
    paramiko = None
    logging.warning("paramiko no está instalado. Instala con: pip install paramiko")

logger = logging.getLogger(__name__)

# Configuración de WireGuard desde variables de entorno
WG_SERVER_HOST = getattr(settings, 'WG_SERVER_HOST', os.getenv('WG_SERVER_HOST', ''))
WG_SERVER_USER = getattr(settings, 'WG_SERVER_USER', os.getenv('WG_SERVER_USER', 'root'))
WG_SERVER_PASSWORD = getattr(settings, 'WG_SERVER_PASSWORD', os.getenv('WG_SERVER_PASSWORD', ''))
WG_SERVER_SSH_PORT = int(getattr(settings, 'WG_SERVER_SSH_PORT', os.getenv('WG_SERVER_SSH_PORT', '22')))
WG_INTERFACE = getattr(settings, 'WG_INTERFACE', os.getenv('WG_INTERFACE', 'wg0'))
WG_CONFIG_DIR = getattr(settings, 'WG_CONFIG_DIR', os.getenv('WG_CONFIG_DIR', '/etc/wireguard'))
WG_SERVER_IP = getattr(settings, 'WG_SERVER_IP', os.getenv('WG_SERVER_IP', '10.8.0.1'))
WG_SERVER_PORT = int(getattr(settings, 'WG_SERVER_PORT', os.getenv('WG_SERVER_PORT', '51820')))
WG_SERVER_PUBLIC_KEY_PATH = getattr(settings, 'WG_SERVER_PUBLIC_KEY_PATH', os.getenv('WG_SERVER_PUBLIC_KEY_PATH', '/etc/wireguard/public.key'))
WG_SERVER_ENDPOINT = getattr(settings, 'WG_SERVER_ENDPOINT', os.getenv('WG_SERVER_ENDPOINT', ''))
WG_SSH_KEY_PATH = getattr(settings, 'WG_SSH_KEY_PATH', os.getenv('WG_SSH_KEY_PATH', ''))  # Ruta a clave SSH privada (opcional, alternativa a password)


class WireGuardManager:
    """Gestiona configuraciones de WireGuard vía SSH"""
    
    def __init__(self):
        self.config_dir = WG_CONFIG_DIR
        self.interface = WG_INTERFACE
        self.server_ip = WG_SERVER_IP
        self.server_port = WG_SERVER_PORT
        self.server_endpoint = WG_SERVER_ENDPOINT
        self.ssh_host = WG_SERVER_HOST
        self.ssh_user = WG_SERVER_USER
        self.ssh_password = WG_SERVER_PASSWORD
        self.ssh_port = WG_SERVER_SSH_PORT
        self.ssh_key_path = WG_SSH_KEY_PATH
        
        if not self.ssh_host:
            raise ValueError("WG_SERVER_HOST no está configurado. Configúralo en .env o settings.py")
    
    def _get_ssh_client(self) -> paramiko.SSHClient:
        """
        Crea y conecta un cliente SSH al servidor WireGuard.
        
        Returns:
            Cliente SSH conectado
        """
        if not paramiko:
            raise Exception("paramiko no está instalado. Instala con: pip install paramiko")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Intentar con clave SSH primero (más seguro)
            if self.ssh_key_path and Path(self.ssh_key_path).exists():
                client.connect(
                    hostname=self.ssh_host,
                    port=self.ssh_port,
                    username=self.ssh_user,
                    key_filename=self.ssh_key_path,
                    timeout=10
                )
            elif self.ssh_password:
                # Usar password si no hay clave SSH
                client.connect(
                    hostname=self.ssh_host,
                    port=self.ssh_port,
                    username=self.ssh_user,
                    password=self.ssh_password,
                    timeout=10
                )
            else:
                raise ValueError("Debes configurar WG_SERVER_PASSWORD o WG_SSH_KEY_PATH")
            
            return client
        except Exception as e:
            logger.error(f"Error conectando SSH a {self.ssh_host}: {e}")
            raise Exception(f"Error conectando al servidor WireGuard: {e}")
    
    def _execute_ssh_command(self, command: str) -> Tuple[int, str, str]:
        """
        Ejecuta un comando en el servidor remoto vía SSH.
        
        Args:
            command: Comando a ejecutar
        
        Returns:
            Tupla (exit_status, stdout, stderr)
        """
        client = self._get_ssh_client()
        try:
            stdin, stdout, stderr = client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            return exit_status, stdout_text, stderr_text
        finally:
            client.close()
        
    def _get_server_public_key(self) -> str:
        """
        Obtiene la clave pública del servidor WireGuard.
        Intenta múltiples métodos hasta encontrar la clave.
        Prioriza 'wg show' porque es el más confiable (muestra la clave real de la interfaz activa).
        
        Returns:
            Clave pública del servidor o placeholder si no se encuentra
        """
        # Método 1: Leer desde wg show (interfaz activa) - MÁS CONFIABLE (PRIORIDAD)
        # Este método muestra la clave pública real de la interfaz activa
        try:
            exit_status, wg_output, stderr = self._execute_ssh_command(
                f'sudo wg show {self.interface}'
            )
            if exit_status == 0:
                for line in wg_output.split('\n'):
                    line_lower = line.lower()
                    # Buscar línea con "public key:" (puede tener espacios antes)
                    if 'public key:' in line_lower:
                        # Extraer la clave después de "public key:"
                        # El formato es: "  public key: UPgAgldMaBpK9/cAGh3C5+HXkX+n4NtHqAbQjkfL3h0="
                        parts = line.split(':')
                        if len(parts) >= 2:
                            key = parts[-1].strip()  # Tomar la última parte después del último ":"
                            if key and len(key) > 20:  # Validar que sea una clave válida (mínimo 20 caracteres)
                                logger.info(f"✅ Clave pública del servidor obtenida desde 'wg show {self.interface}': {key[:20]}...")
                                return key
        except Exception as e:
            logger.warning(f"No se pudo leer clave pública desde 'wg show': {e}")
        
        # Método 2: Leer desde archivo public.key (fallback)
        try:
            exit_status, server_pub_key, stderr = self._execute_ssh_command(
                f'cat {WG_SERVER_PUBLIC_KEY_PATH} 2>/dev/null || echo ""'
            )
            if exit_status == 0 and server_pub_key.strip():
                key = server_pub_key.strip()
                if key and key != "REEMPLAZAR_CON_CLAVE_PUBLICA_DEL_SERVIDOR" and len(key) > 20:
                    logger.info(f"Clave pública del servidor obtenida desde {WG_SERVER_PUBLIC_KEY_PATH}")
                    return key
        except Exception as e:
            logger.warning(f"No se pudo leer clave pública desde archivo: {e}")
        
        # Método 3: Leer desde archivo de configuración del servidor
        try:
            config_file = f'{self.config_dir}/{self.interface}.conf'
            exit_status, config_content, stderr = self._execute_ssh_command(
                f'cat {config_file} 2>/dev/null | grep -i "publickey" | head -1 || echo ""'
            )
            if exit_status == 0 and config_content.strip():
                # Buscar clave pública en el contenido
                for line in config_content.split('\n'):
                    if 'PublicKey' in line or 'PUBLICKEY' in line.upper():
                        parts = line.split('=')
                        if len(parts) > 1:
                            key = parts[1].strip()
                            if key:
                                logger.info(f"Clave pública del servidor obtenida desde {config_file}")
                                return key
        except Exception as e:
            logger.warning(f"No se pudo leer clave pública desde archivo de configuración: {e}")
        
        # Método 4: Generar desde clave privada si existe
        try:
            private_key_file = f'{self.config_dir}/{self.interface}.key'
            exit_status, private_key, stderr = self._execute_ssh_command(
                f'cat {private_key_file} 2>/dev/null || echo ""'
            )
            if exit_status == 0 and private_key.strip():
                # Generar clave pública desde la privada
                exit_status, public_key, stderr = self._execute_ssh_command(
                    f'echo "{private_key.strip()}" | wg pubkey'
                )
                if exit_status == 0 and public_key.strip():
                    key = public_key.strip()
                    logger.info(f"Clave pública del servidor generada desde clave privada")
                    return key
        except Exception as e:
            logger.warning(f"No se pudo generar clave pública desde clave privada: {e}")
        
        # Si no se encontró, retornar placeholder
        logger.error(f"No se pudo obtener la clave pública del servidor. Revisa la configuración.")
        return "REEMPLAZAR_CON_CLAVE_PUBLICA_DEL_SERVIDOR"
    
    def generate_keypair(self) -> Tuple[str, str]:
        """
        Genera un par de claves pública/privada para WireGuard en el servidor remoto.
        Retorna: (private_key, public_key)
        """
        try:
            # Generar clave privada en el servidor remoto
            exit_status, private_key, stderr = self._execute_ssh_command('wg genkey')
            if exit_status != 0:
                raise Exception(f"Error generando clave privada: {stderr}")
            private_key = private_key.strip()
            
            # Generar clave pública desde la privada
            exit_status, public_key, stderr = self._execute_ssh_command(f'echo "{private_key}" | wg pubkey')
            if exit_status != 0:
                raise Exception(f"Error generando clave pública: {stderr}")
            public_key = public_key.strip()
            
            return private_key, public_key
        except Exception as e:
            logger.error(f"Error generando claves WireGuard: {e}")
            raise
    
    def get_next_available_ip(self) -> str:
        """
        Obtiene la siguiente IP disponible en la red VPN.
        Consulta las IPs ya asignadas desde la BD y asigna la siguiente disponible.
        """
        from ..models import VpnConfig
        
        # Obtener todas las IPs asignadas
        assigned_ips = set(
            VpnConfig.objects.exclude(ip_address__isnull=True)
            .exclude(ip_address='')
            .values_list('ip_address', flat=True)
        )
        
        # Obtener también las IPs de los peers activos en el servidor (para evitar conflictos)
        try:
            exit_status, wg_output, _ = self._execute_ssh_command(f'sudo wg show {self.interface} dump')
            if exit_status == 0:
                for line in wg_output.strip().split('\n'):
                    if line and not line.startswith('interface:'):
                        parts = line.split('\t')
                        if len(parts) >= 4:
                            # El formato es: public_key, preshared_key, endpoint, allowed_ips, ...
                            allowed_ips = parts[3] if len(parts) > 3 else ''
                            if allowed_ips and '/' in allowed_ips:
                                peer_ip = allowed_ips.split('/')[0]
                                assigned_ips.add(peer_ip)
        except Exception as e:
            logger.warning(f"No se pudieron obtener IPs de peers activos: {e}")
        
        # Buscar la siguiente IP disponible desde .2 hasta .254
        # Usar la misma red que el servidor (ej: si servidor es 10.8.3.1, buscar en 10.8.3.x)
        base_ip = self.server_ip.rsplit('.', 1)[0]  # Obtener "10.8.3" desde "10.8.3.1"
        for i in range(2, 255):  # Desde .2 hasta .254
            candidate_ip = f"{base_ip}.{i}"
            if candidate_ip not in assigned_ips:
                return candidate_ip
        
        raise Exception(f"No hay IPs disponibles en el rango {base_ip}.2-254")
    
    def create_client_config(
        self,
        client_name: str,
        client_private_key: str,
        client_public_key: str,
        client_ip: str,
        server_public_key: Optional[str] = None
    ) -> str:
        """
        Genera el contenido del archivo .conf para el cliente.
        
        Args:
            client_name: Nombre del cliente
            client_private_key: Clave privada del cliente
            client_public_key: Clave pública del cliente
            client_ip: IP asignada al cliente
            server_public_key: Clave pública del servidor (si no se proporciona, se lee del archivo)
        
        Returns:
            Contenido del archivo .conf como string
        """
        # Leer clave pública del servidor si no se proporciona
        if not server_public_key:
            server_public_key = self._get_server_public_key()
        
        # Validar que la clave pública no sea el placeholder
        if server_public_key == "REEMPLAZAR_CON_CLAVE_PUBLICA_DEL_SERVIDOR":
            logger.error("No se pudo obtener la clave pública del servidor en create_client_config")
            raise ValueError("No se pudo obtener la clave pública del servidor. Verifica la configuración de WireGuard.")
        
        # Configuración de red: Cliente solo puede acceder a su propia IP
        # El servidor puede acceder al cliente porque tiene AllowedIPs = client_ip/32 en el servidor
        # Pero el cliente NO puede acceder al servidor ni a otros clientes
        client_allowed_ips = f"{client_ip}/32"  # Solo su propia IP
        
        # Asegurar que server_endpoint tenga un valor por defecto
        endpoint = self.server_endpoint or 'TU_SERVIDOR:51820'
        
        config_content = f"""# Configuración WireGuard para {client_name}
# Generado automáticamente por EDDESO
# Configuración: Cliente solo puede acceder a su propia IP
# El servidor puede acceder a este cliente, pero este cliente NO puede acceder al servidor ni a otros clientes

[Interface]
PrivateKey = {client_private_key}
Address = {client_ip}/24
DNS = 8.8.8.8

[Peer]
PublicKey = {server_public_key}
Endpoint = {endpoint}
AllowedIPs = {client_allowed_ips}
PersistentKeepalive = 25
"""
        return config_content
    
    def save_config_file(self, client_name: str, config_content: str) -> str:
        """
        Guarda el archivo .conf en el sistema de archivos.
        
        Args:
            client_name: Nombre del cliente (se sanitiza para el nombre de archivo)
            config_content: Contenido del archivo .conf
        
        Returns:
            Ruta del archivo guardado
        """
        # Crear directorio si no existe
        output_dir = Path('/tmp/wireguard_configs')  # Cambiar a un directorio apropiado
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitizar nombre para el archivo
        safe_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_').lower()
        
        config_file_path = output_dir / f"{safe_name}.conf"
        
        try:
            config_file_path.write_text(config_content)
            logger.info(f"Archivo de configuración guardado en: {config_file_path}")
            return str(config_file_path)
        except Exception as e:
            logger.error(f"Error guardando archivo de configuración: {e}")
            raise
    
    def add_peer_to_server(self, client_public_key: str, client_ip: str) -> bool:
        """
        Agrega un peer (cliente) a la configuración del servidor WireGuard vía SSH.
        Esto requiere ejecutar: wg set {interface} peer {public_key} allowed-ips {ip}/32
        
        Args:
            client_public_key: Clave pública del cliente
            client_ip: IP asignada al cliente
        
        Returns:
            True si se agregó exitosamente
        """
        try:
            # Escapar la clave pública para el comando
            escaped_key = client_public_key.replace('"', '\\"')
            command = f'sudo wg set {self.interface} peer "{escaped_key}" allowed-ips {client_ip}/32'
            
            exit_status, stdout, stderr = self._execute_ssh_command(command)
            
            if exit_status == 0:
                logger.info(f"Peer agregado: {client_ip} ({client_public_key[:20]}...)")
                return True
            else:
                logger.error(f"Error agregando peer al servidor: {stderr}")
                return False
        except Exception as e:
            logger.error(f"Error inesperado agregando peer: {e}")
            return False
    
    def remove_peer_from_server(self, client_public_key: str) -> bool:
        """
        Remueve un peer del servidor WireGuard vía SSH.
        
        Args:
            client_public_key: Clave pública del cliente a remover
        
        Returns:
            True si se removió exitosamente
        """
        try:
            # Escapar la clave pública para el comando
            escaped_key = client_public_key.replace('"', '\\"')
            command = f'sudo wg set {self.interface} peer "{escaped_key}" remove'
            
            exit_status, stdout, stderr = self._execute_ssh_command(command)
            
            if exit_status == 0:
                logger.info(f"Peer removido: {client_public_key[:20]}...")
                return True
            else:
                logger.error(f"Error removiendo peer: {stderr}")
                return False
        except Exception as e:
            logger.error(f"Error inesperado removiendo peer: {e}")
            return False
    
    def get_server_status(self) -> Dict:
        """
        Obtiene el estado actual del servidor WireGuard vía SSH.
        
        Returns:
            Diccionario con información del servidor
        """
        try:
            exit_status, stdout, stderr = self._execute_ssh_command(f'sudo wg show {self.interface}')
            
            if exit_status == 0:
                return {
                    'status': 'active',
                    'output': stdout
                }
            else:
                return {
                    'status': 'inactive',
                    'output': stderr
                }
        except Exception as e:
            logger.error(f"Error obteniendo estado del servidor: {e}")
            return {
                'status': 'error',
                'output': str(e)
            }
    
    def get_peer_stats(self, public_key: Optional[str] = None) -> Dict:
        """
        Obtiene estadísticas detalladas de los peers.
        El formato de 'wg show dump' es:
        public_key, preshared_key, endpoint, allowed_ips, last_handshake, tx_bytes, rx_bytes, persistent_keepalive
        
        Args:
            public_key: Clave pública del peer específico (opcional, si no se proporciona retorna todos)
        
        Returns:
            Diccionario con estadísticas de los peers
        """
        try:
            exit_status, stdout, stderr = self._execute_ssh_command(f'sudo wg show {self.interface} dump')
            
            if exit_status != 0:
                return {
                    'error': stderr,
                    'peers': []
                }
            
            peers_data = []
            lines = stdout.strip().split('\n')
            
            # La primera línea es la interfaz, las siguientes son los peers
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 8:
                    peer_public_key = parts[0]
                    preshared_key = parts[1] if parts[1] != '(none)' else None
                    endpoint = parts[2] if parts[2] != '(none)' else None
                    allowed_ips = parts[3] if parts[3] else ''
                    last_handshake = int(parts[4]) if parts[4] != '0' else None
                    tx_bytes = int(parts[5]) if parts[5] else 0
                    rx_bytes = int(parts[6]) if parts[6] else 0
                    persistent_keepalive = int(parts[7]) if parts[7] else None
                    
                    # Extraer IP del allowed_ips
                    ip_address = allowed_ips.split('/')[0] if '/' in allowed_ips else ''
                    
                    # Si se especificó una clave pública, solo retornar ese peer
                    if public_key and peer_public_key != public_key:
                        continue
                    
                    # Calcular tiempo desde último handshake
                    if last_handshake:
                        from datetime import datetime, timezone
                        handshake_time = datetime.fromtimestamp(last_handshake, tz=timezone.utc)
                        now = datetime.now(timezone.utc)
                        seconds_ago = int((now - handshake_time).total_seconds())
                    else:
                        seconds_ago = None
                    
                    peers_data.append({
                        'public_key': peer_public_key,
                        'ip_address': ip_address,
                        'endpoint': endpoint,
                        'last_handshake': last_handshake,
                        'last_handshake_seconds_ago': seconds_ago,
                        'tx_bytes': tx_bytes,
                        'rx_bytes': rx_bytes,
                        'total_bytes': tx_bytes + rx_bytes,
                        'persistent_keepalive': persistent_keepalive,
                        'connected': seconds_ago is not None and seconds_ago < 180  # Conectado si handshake < 3 minutos
                    })
            
            return {
                'peers': peers_data,
                'total_peers': len(peers_data)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de peers: {e}")
            return {
                'error': str(e),
                'peers': []
            }
    
    def sync_existing_peers(self) -> Dict:
        """
        Sincroniza los peers existentes en el servidor con la base de datos.
        Crea registros VpnConfig para peers que existen en el servidor pero no en la BD.
        
        Returns:
            Diccionario con información de la sincronización
        """
        from ..models import VpnConfig
        
        try:
            # Obtener estadísticas de todos los peers del servidor
            stats = self.get_peer_stats()
            
            if 'error' in stats:
                return {
                    'error': stats['error'],
                    'created': 0,
                    'existing': 0
                }
            
            created_count = 0
            existing_count = 0
            
            for peer in stats.get('peers', []):
                public_key = peer.get('public_key')
                ip_address = peer.get('ip_address')
                
                if not public_key:
                    continue
                
                # Verificar si ya existe en la BD
                try:
                    vpn_config = VpnConfig.objects.get(public_key=public_key)
                    existing_count += 1
                    # Actualizar IP si cambió
                    if ip_address and vpn_config.ip_address != ip_address:
                        vpn_config.ip_address = ip_address
                        vpn_config.save()
                except VpnConfig.DoesNotExist:
                    # Crear nuevo registro
                    nombre = f"Peer {ip_address}" if ip_address else f"Peer {public_key[:20]}..."
                    
                    VpnConfig.objects.create(
                        nombre=nombre,
                        ip_address=ip_address,
                        public_key=public_key,
                        private_key=None,  # No tenemos la clave privada de peers existentes
                        activo=True,
                        notas=f"Importado automáticamente desde el servidor"
                    )
                    created_count += 1
            
            return {
                'created': created_count,
                'existing': existing_count,
                'total_peers': len(stats.get('peers', []))
            }
            
        except Exception as e:
            logger.error(f"Error sincronizando peers: {e}", exc_info=True)
            return {
                'error': str(e),
                'created': 0,
                'existing': 0
            }
    
    def create_client(
        self,
        nombre: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Crea una nueva configuración de cliente VPN.
        
        Args:
            nombre: Nombre descriptivo del cliente
            ip_address: IP deseada (opcional, se asigna automáticamente si no se proporciona)
        
        Returns:
            Diccionario con: private_key, public_key, ip_address, config_content, config_file_path
        """
        # Generar claves
        private_key, public_key = self.generate_keypair()
        
        # Asignar IP si no se proporciona
        if not ip_address:
            ip_address = self.get_next_available_ip()
        
        # Generar contenido del archivo .conf
        config_content = self.create_client_config(
            client_name=nombre,
            client_private_key=private_key,
            client_public_key=public_key,
            client_ip=ip_address
        )
        
        # Guardar archivo
        config_file_path = self.save_config_file(nombre, config_content)
        
        # Agregar peer al servidor
        peer_added = self.add_peer_to_server(public_key, ip_address)
        if not peer_added:
            logger.warning(f"No se pudo agregar el peer al servidor, pero la configuración se creó")
        
        return {
            'private_key': private_key,
            'public_key': public_key,
            'ip_address': ip_address,
            'config_content': config_content,
            'config_file_path': config_file_path
        }

