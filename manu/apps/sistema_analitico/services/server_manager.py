# sistema_analitico/services/server_manager.py
"""
Servicio para gestionar servicios del sistema (systemd) y PM2 vía SSH.
Permite ver estado, iniciar, detener, reiniciar servicios y ver logs.
"""
import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings
import os

try:
    import paramiko
except ImportError:
    paramiko = None
    logging.warning("paramiko no está instalado. Instala con: pip install paramiko")

logger = logging.getLogger(__name__)

# Configuración SSH desde variables de entorno (específica para gestión de servicios)
# Estas variables son independientes de WireGuard y apuntan al servidor VPS donde están los servicios
SSH_HOST = getattr(settings, 'SERVER_SSH_HOST', os.getenv('SERVER_SSH_HOST', ''))
SSH_USER = getattr(settings, 'SERVER_SSH_USER', os.getenv('SERVER_SSH_USER', 'root'))
SSH_PASSWORD = getattr(settings, 'SERVER_SSH_PASSWORD', os.getenv('SERVER_SSH_PASSWORD', ''))
SSH_PORT = int(getattr(settings, 'SERVER_SSH_PORT', os.getenv('SERVER_SSH_PORT', '22')))
SSH_KEY_PATH = getattr(settings, 'SERVER_SSH_KEY_PATH', os.getenv('SERVER_SSH_KEY_PATH', ''))


class ServerManager:
    """Gestiona servicios del sistema y PM2 vía SSH o localmente"""
    
    def __init__(self):
        self.ssh_host = SSH_HOST
        self.ssh_user = SSH_USER
        self.ssh_password = SSH_PASSWORD
        self.ssh_port = SSH_PORT
        self.ssh_key_path = SSH_KEY_PATH
        
        # Si no hay SSH_HOST configurado o es localhost/127.0.0.1, ejecutar localmente
        self.use_local = not self.ssh_host or self.ssh_host in ('localhost', '127.0.0.1', '::1')
        
        if not self.use_local and not self.ssh_host:
            raise ValueError("SSH_HOST no está configurado. Configura SERVER_SSH_HOST en .env o déjalo vacío para ejecución local")
    
    def _get_ssh_client(self) -> paramiko.SSHClient:
        """Crea y conecta un cliente SSH"""
        if not paramiko:
            raise Exception("paramiko no está instalado. Instala con: pip install paramiko")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                client.connect(
                    hostname=self.ssh_host,
                    port=self.ssh_port,
                    username=self.ssh_user,
                    key_filename=self.ssh_key_path,
                    timeout=10
                )
            elif self.ssh_password:
                client.connect(
                    hostname=self.ssh_host,
                    port=self.ssh_port,
                    username=self.ssh_user,
                    password=self.ssh_password,
                    timeout=10
                )
            else:
                raise ValueError("Debes configurar SERVER_SSH_PASSWORD o SERVER_SSH_KEY_PATH en .env")
            
            return client
        except Exception as e:
            logger.error(f"Error conectando SSH a {self.ssh_host}: {e}")
            raise Exception(f"Error conectando al servidor: {e}")
    
    def _execute_command(self, command: str, use_sudo: bool = False) -> Tuple[int, str, str]:
        """
        Ejecuta un comando en el servidor remoto vía SSH o localmente.
        
        Args:
            command: Comando a ejecutar
            use_sudo: Si True, ejecuta con sudo
        
        Returns:
            Tupla (exit_status, stdout, stderr)
        """
        if use_sudo:
            command = f"sudo {command}"
        
        # Si está configurado para ejecución local, usar subprocess directamente
        if self.use_local:
            import subprocess
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return result.returncode, result.stdout, result.stderr
            except subprocess.TimeoutExpired:
                return 1, '', 'Comando expiró (timeout)'
            except Exception as e:
                logger.error(f"Error ejecutando comando local: {e}")
                return 1, '', str(e)
        
        # Ejecutar vía SSH si no es local
        client = self._get_ssh_client()
        try:
            stdin, stdout, stderr = client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode('utf-8', errors='ignore')
            stderr_text = stderr.read().decode('utf-8', errors='ignore')
            return exit_status, stdout_text, stderr_text
        finally:
            client.close()
    
    def get_systemd_services(self) -> List[Dict]:
        """
        Obtiene lista de servicios systemd con su estado.
        
        Returns:
            Lista de diccionarios con información de servicios
        """
        try:
            # Obtener servicios activos e inactivos
            exit_status, stdout, stderr = self._execute_command(
                "systemctl list-units --type=service --all --no-pager --no-legend",
                use_sudo=True
            )
            
            services = []
            for line in stdout.strip().split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) < 4:
                    continue
                
                service_name = parts[0]
                load_state = parts[1]  # loaded, not-found, etc
                active_state = parts[2]  # active, inactive, failed, etc
                sub_state = parts[3]  # running, dead, etc
                
                # Obtener descripción
                desc_exit, desc_stdout, _ = self._execute_command(
                    f"systemctl show -p Description --value {service_name}",
                    use_sudo=True
                )
                description = desc_stdout.strip() if desc_exit == 0 else service_name
                
                services.append({
                    'name': service_name,
                    'description': description,
                    'load_state': load_state,
                    'active_state': active_state,
                    'sub_state': sub_state,
                    'status': 'active' if active_state == 'active' else 'inactive',
                    'running': active_state == 'active' and sub_state == 'running'
                })
            
            return sorted(services, key=lambda x: x['name'])
        except Exception as e:
            logger.error(f"Error obteniendo servicios systemd: {e}")
            raise Exception(f"Error obteniendo servicios: {str(e)}")
    
    def get_pm2_processes(self) -> List[Dict]:
        """
        Obtiene lista de procesos PM2.
        
        Returns:
            Lista de diccionarios con información de procesos PM2
        """
        try:
            # Primero verificar que PM2 esté instalado
            exit_status, stdout, stderr = self._execute_command("which pm2")
            if exit_status != 0:
                logger.warning("PM2 no está instalado o no está en el PATH")
                return []
            
            # Obtener lista de procesos en formato JSON
            exit_status, stdout, stderr = self._execute_command("pm2 jlist")
            
            if exit_status != 0:
                logger.warning(f"Error ejecutando pm2 jlist: {stderr}")
                return []
            
            if not stdout.strip():
                logger.info("PM2 no tiene procesos corriendo")
                return []
            
            import json
            try:
                processes = json.loads(stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando salida de PM2: {e}")
                logger.error(f"Salida recibida: {stdout[:200]}")  # Primeros 200 caracteres para debug
                # Intentar con pm2 list en formato JSON alternativo
                exit_status2, stdout2, stderr2 = self._execute_command("pm2 list --format json")
                if exit_status2 == 0 and stdout2.strip():
                    try:
                        processes = json.loads(stdout2)
                    except:
                        return []
                else:
                    return []
            
            if not isinstance(processes, list):
                logger.warning("PM2 jlist no devolvió una lista")
                return []
            
            result = []
            import time
            current_time_ms = int(time.time() * 1000)
            
            for proc in processes:
                if not isinstance(proc, dict):
                    continue
                    
                pm2_env = proc.get('pm2_env', {})
                monit = proc.get('monit', {})
                
                # Calcular uptime (tiempo desde que se inició)
                pm_uptime = pm2_env.get('pm_uptime', 0)
                uptime_seconds = 0
                if pm_uptime:
                    uptime_seconds = (current_time_ms - pm_uptime) // 1000  # Convertir a segundos
                
                # Convertir memoria de bytes a número
                memory_bytes = monit.get('memory', 0)
                if isinstance(memory_bytes, str):
                    # Si viene como string "87.2mb", extraer el número
                    try:
                        memory_str = memory_bytes.lower().replace('mb', '').replace('gb', '').replace('kb', '').strip()
                        memory_num = float(memory_str)
                        if 'gb' in memory_bytes.lower():
                            memory_bytes = int(memory_num * 1024 * 1024 * 1024)
                        elif 'mb' in memory_bytes.lower():
                            memory_bytes = int(memory_num * 1024 * 1024)
                        elif 'kb' in memory_bytes.lower():
                            memory_bytes = int(memory_num * 1024)
                        else:
                            memory_bytes = int(memory_num)
                    except:
                        memory_bytes = 0
                elif not isinstance(memory_bytes, (int, float)):
                    memory_bytes = 0
                
                result.append({
                    'id': proc.get('pm_id', proc.get('id', 0)),
                    'name': proc.get('name', 'unknown'),
                    'status': pm2_env.get('status', 'unknown'),
                    'uptime': uptime_seconds,
                    'restarts': pm2_env.get('restart_time', 0),
                    'cpu': float(monit.get('cpu', 0)) if monit.get('cpu') else 0.0,
                    'memory': int(memory_bytes),
                    'pid': proc.get('pid', 0),
                    'mode': pm2_env.get('exec_mode', 'unknown')
                })
            
            return result
        except Exception as e:
            logger.error(f"Error obteniendo procesos PM2: {e}", exc_info=True)
            # PM2 puede no estar instalado o no tener procesos
            return []
    
    def systemd_action(self, service_name: str, action: str) -> Dict:
        """
        Ejecuta una acción sobre un servicio systemd.
        
        Args:
            service_name: Nombre del servicio
            action: start, stop, restart, reload, status
        
        Returns:
            Diccionario con resultado de la operación
        """
        valid_actions = ['start', 'stop', 'restart', 'reload', 'status']
        if action not in valid_actions:
            raise ValueError(f"Acción inválida. Debe ser una de: {', '.join(valid_actions)}")
        
        try:
            exit_status, stdout, stderr = self._execute_command(
                f"systemctl {action} {service_name}",
                use_sudo=True
            )
            
            return {
                'success': exit_status == 0,
                'exit_status': exit_status,
                'stdout': stdout,
                'stderr': stderr,
                'message': stdout if exit_status == 0 else stderr
            }
        except Exception as e:
            logger.error(f"Error ejecutando {action} en {service_name}: {e}")
            raise Exception(f"Error ejecutando acción: {str(e)}")
    
    def pm2_action(self, process_name: str, action: str) -> Dict:
        """
        Ejecuta una acción sobre un proceso PM2.
        
        Args:
            process_name: Nombre o ID del proceso
            action: start, stop, restart, reload, delete
        
        Returns:
            Diccionario con resultado de la operación
        """
        valid_actions = ['start', 'stop', 'restart', 'reload', 'delete']
        if action not in valid_actions:
            raise ValueError(f"Acción inválida. Debe ser una de: {', '.join(valid_actions)}")
        
        try:
            exit_status, stdout, stderr = self._execute_command(
                f"pm2 {action} {process_name}"
            )
            
            return {
                'success': exit_status == 0,
                'exit_status': exit_status,
                'stdout': stdout,
                'stderr': stderr,
                'message': stdout if exit_status == 0 else stderr
            }
        except Exception as e:
            logger.error(f"Error ejecutando {action} en {process_name}: {e}")
            raise Exception(f"Error ejecutando acción: {str(e)}")
    
    def get_service_logs(self, service_name: str, lines: int = 100, service_type: str = 'systemd') -> str:
        """
        Obtiene logs de un servicio.
        
        Args:
            service_name: Nombre del servicio
            lines: Número de líneas a obtener
            service_type: 'systemd' o 'pm2'
        
        Returns:
            Logs del servicio
        """
        try:
            if service_type == 'systemd':
                exit_status, stdout, stderr = self._execute_command(
                    f"journalctl -u {service_name} -n {lines} --no-pager",
                    use_sudo=True
                )
            elif service_type == 'pm2':
                exit_status, stdout, stderr = self._execute_command(
                    f"pm2 logs {service_name} --lines {lines} --nostream"
                )
            else:
                raise ValueError("service_type debe ser 'systemd' o 'pm2'")
            
            return stdout if exit_status == 0 else stderr
        except Exception as e:
            logger.error(f"Error obteniendo logs de {service_name}: {e}")
            raise Exception(f"Error obteniendo logs: {str(e)}")
    
    def get_system_info(self) -> Dict:
        """
        Obtiene información general del sistema.
        
        Returns:
            Diccionario con información del sistema
        """
        try:
            info = {}
            
            # Uptime
            exit_status, stdout, _ = self._execute_command("uptime -p")
            info['uptime'] = stdout.strip() if exit_status == 0 else "N/A"
            
            # Load average
            exit_status, stdout, _ = self._execute_command("uptime")
            if exit_status == 0:
                parts = stdout.split('load average:')
                if len(parts) > 1:
                    info['load_average'] = parts[1].strip()
                else:
                    info['load_average'] = "N/A"
            else:
                info['load_average'] = "N/A"
            
            # Memoria
            exit_status, stdout, _ = self._execute_command("free -h")
            info['memory'] = stdout if exit_status == 0 else "N/A"
            
            # Disco
            exit_status, stdout, _ = self._execute_command("df -h /")
            info['disk'] = stdout if exit_status == 0 else "N/A"
            
            return info
        except Exception as e:
            logger.error(f"Error obteniendo información del sistema: {e}")
            return {'error': str(e)}
    
    def execute_command(self, command: str, use_sudo: bool = False) -> Dict:
        """
        Ejecuta un comando arbitrario en el servidor remoto vía SSH.
        
        Args:
            command: Comando a ejecutar
            use_sudo: Si True, ejecuta con sudo
        
        Returns:
            Diccionario con resultado de la operación
        """
        try:
            exit_status, stdout, stderr = self._execute_command(command, use_sudo=use_sudo)
            
            return {
                'success': exit_status == 0,
                'exit_status': exit_status,
                'stdout': stdout,
                'stderr': stderr,
                'command': command,
                'output': stdout if exit_status == 0 else stderr
            }
        except Exception as e:
            logger.error(f"Error ejecutando comando: {e}")
            return {
                'success': False,
                'exit_status': -1,
                'stdout': '',
                'stderr': str(e),
                'command': command,
                'output': f'Error: {str(e)}'
            }

