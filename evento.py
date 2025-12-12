import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
import threading
from datetime import datetime
import sys
import os
import firebirdsql

class ConnectionPool:
    def __init__(self):
        self.pool = {}
        self.lock = threading.Lock()
    
    def get_connection(self, db_path):
        """Obtiene conexión del pool o crea nueva"""
        with self.lock:
            if db_path not in self.pool:
                self.pool[db_path] = []
            
            if self.pool[db_path]:
                print(f"🔁 Reutilizando conexión de pool para: {db_path}")
                return self.pool[db_path].pop()
            else:
                print(f"🆕 Creando nueva conexión para: {db_path}")
                return self.conectar_firebird(db_path)
    
    def return_connection(self, db_path, connection):
        """Devuelve conexión al pool"""
        with self.lock:
            if db_path not in self.pool:
                self.pool[db_path] = []
            self.pool[db_path].append(connection)
    
    def conectar_firebird(self, ruta_db):
        """Conexión a base de datos Firebird"""
        try:
            return firebirdsql.connect(
                host='localhost',
                database=ruta_db,
                user='SYSDBA',
                password='masterkey',
                charset='ISO8859_1'
            )
        except Exception as e:
            raise Exception(f"Error de conexión: {str(e)}")

class DianEventsApp:
    def __init__(self, root, db_path=None, identification=None, first_name=None, last_name=None, 
                 department=None, job_title=None, kardex_id=None, prefijo=None, numero=None):
        self.root = root
        self.db_path = db_path
        self.kardex_id = kardex_id
        self.prefijo = prefijo
        self.numero = numero
        self.connection_pool = ConnectionPool()
        
        self.root.title("DIAN Events Manager - Búsqueda Automática")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Variables con los parámetros recibidos
        self.cufe_var = tk.StringVar()
        self.identification_var = tk.StringVar(value=identification or "")
        self.first_name_var = tk.StringVar(value=first_name or "")
        self.last_name_var = tk.StringVar(value=last_name or "")
        self.department_var = tk.StringVar(value=department or "")
        self.job_title_var = tk.StringVar(value=job_title or "")
        self.prefijo_var = tk.StringVar(value=prefijo or "")
        self.numero_var = tk.StringVar(value=numero or "")
        
        # Variables para empresas
        self.empresa_seleccionada = tk.StringVar()
        self.año_seleccionado = tk.StringVar()
        self.empresas_data = []
        self.empresas_agrupadas = {}
        
        # Diccionario de eventos
        self.events = {
            1: "Acuse de recibo de Factura Electrónica de Venta",
            2: "Reclamo de la Factura Electrónica de Venta",
            3: "Recibo del bien y/o prestación del servicio",
            4: "Aceptación expresa",
            5: "Aceptación Tácita",
            6: "Documento validado por la DIAN",
            7: "Documento rechazado por la DIAN"
        }
        
        # Variables para checkboxes
        self.event_vars = {}
        for event_id in self.events:
            self.event_vars[event_id] = tk.BooleanVar()
        
        # Configuración de DIAN
        self.config = None
        
        # Ruta de la base de datos ADMIN (quemada)
        self.admin_db_path = "C:/Visual TNS/ADMIN.GDB"
        # Ruta actual de la base de datos en uso
        self.current_db_path = None
        
        self.setup_ui()
        self.cargar_empresas_desde_admin()
        self.cargar_configuracion()
        
        # Si tenemos prefijo y número, buscar automáticamente
        if self.prefijo and self.numero:
            self.buscar_kardex_automaticamente()
    
    def conectar_admin(self):
        """Conecta a la base de datos ADMIN"""
        try:
            return firebirdsql.connect(
                host='localhost',
                database=self.admin_db_path,
                user='SYSDBA',
                password='masterkey',
                charset='ISO8859_1'
            )
        except Exception as e:
            self.log_message(f"❌ Error conectando a ADMIN: {str(e)}", 'ERROR')
            return None
    
    def cargar_empresas_desde_admin(self):
        """Carga las empresas desde la base de datos ADMIN con filtro por año actual"""
        conexion = None
        try:
            conexion = self.conectar_admin()
            if not conexion:
                self.log_message("❌ No se pudo conectar a ADMIN para cargar empresas", 'ERROR')
                return
            
            cursor = conexion.cursor()
            
            # Obtener año actual para filtrar
            año_actual = datetime.now().year
            
            # Consulta para obtener empresas filtradas por año actual
            query = """
                SELECT CODIGO, NOMBRE, NIT, ANOFIS, ARCHIVO 
                FROM EMPRESAS 
                WHERE ANOFIS = ? 
                ORDER BY NOMBRE
            """
            cursor.execute(query, (str(año_actual),))
            resultados = cursor.fetchall()
            
            self.empresas_data = []
            self.empresas_agrupadas = {}
            
            for fila in resultados:
                codigo, nombre, nit, anofis, archivo = fila
                empresa_info = {
                    'codigo': codigo,
                    'nombre': nombre,
                    'nit': nit,
                    'anofis': anofis,
                    'archivo': archivo
                }
                self.empresas_data.append(empresa_info)
                
                # Agrupar por NIT
                if nit not in self.empresas_agrupadas:
                    self.empresas_agrupadas[nit] = {
                        'nombre': nombre,
                        'años': []
                    }
                
                self.empresas_agrupadas[nit]['años'].append({
                    'anofis': anofis,
                    'archivo': archivo,
                    'codigo': codigo
                })
            
            # Ordenar años dentro de cada empresa
            for nit in self.empresas_agrupadas:
                self.empresas_agrupadas[nit]['años'].sort(key=lambda x: x['anofis'], reverse=True)
            
            self.log_message(f"✅ Cargadas {len(self.empresas_data)} empresas para el año {año_actual}", 'SUCCESS')
            
            # Actualizar combobox de empresas
            self.actualizar_combo_empresas()
            
        except Exception as e:
            self.log_message(f"❌ Error cargando empresas: {str(e)}", 'ERROR')
        finally:
            if conexion:
                conexion.close()
    
    def actualizar_combo_empresas(self):
        """Actualiza el combobox de empresas con los datos cargados"""
        try:
            if not self.empresas_agrupadas:
                self.log_message("⚠️ No hay empresas disponibles", 'WARNING')
                return
            
            # Ordenar empresas por nombre
            empresas_ordenadas = sorted(
                [(data['nombre'], nit) for nit, data in self.empresas_agrupadas.items()],
                key=lambda x: x[0]
            )
            
            empresas_display = [f"{nombre} - {nit}" for nombre, nit in empresas_ordenadas]
            
            if hasattr(self, 'empresa_combo'):
                self.empresa_combo['values'] = empresas_display
                
                if empresas_display:
                    self.empresa_combo.set(empresas_display[0])
                    self.on_empresa_seleccionada()
                else:
                    self.empresa_combo.set("No hay empresas disponibles")
                    
        except Exception as e:
            self.log_message(f"❌ Error actualizando combo empresas: {str(e)}", 'ERROR')
    
    def on_empresa_seleccionada(self, event=None):
        """Cuando se selecciona una empresa, carga los años disponibles"""
        try:
            empresa_texto = self.empresa_seleccionada.get()
            if not empresa_texto or "No hay" in empresa_texto:
                return
            
            # Extraer NIT de la empresa seleccionada
            nit = empresa_texto.split(' - ')[-1]
            
            # Obtener años disponibles para este NIT
            if nit in self.empresas_agrupadas:
                años_data = self.empresas_agrupadas[nit]['años']
                años_display = [f"{año['anofis']} - {año['codigo']}" for año in años_data]
            else:
                años_display = []
            
            if hasattr(self, 'año_combo'):
                self.año_combo['values'] = años_display
                
                if años_display:
                    # Seleccionar automáticamente el año más reciente
                    self.año_combo.set(años_display[0])
                    self.on_año_seleccionado()
                else:
                    self.año_combo.set("No hay años disponibles")
                    
        except Exception as e:
            self.log_message(f"❌ Error en selección de empresa: {str(e)}", 'ERROR')
    
    def on_año_seleccionado(self, event=None):
        """Cuando se selecciona un año, construye la ruta de la base de datos"""
        try:
            empresa_texto = self.empresa_seleccionada.get()
            año_texto = self.año_seleccionado.get()
            
            if not empresa_texto or not año_texto or "No hay" in año_texto:
                return
            
            # Extraer NIT y año
            nit = empresa_texto.split(' - ')[-1]
            anofis_seleccionado = año_texto.split(' - ')[0]
            
            # Buscar la ruta del archivo en los datos
            ruta_bd = None
            
            if nit in self.empresas_agrupadas:
                for año_data in self.empresas_agrupadas[nit]['años']:
                    if año_data['anofis'] == anofis_seleccionado:
                        ruta_bd = año_data['archivo']
                        break
            
            if ruta_bd and os.path.exists(ruta_bd):
                self.current_db_path = ruta_bd
                if hasattr(self, 'ruta_label'):
                    self.ruta_label.config(text=ruta_bd)
                self.log_message(f"✅ Base de datos seleccionada: {ruta_bd}", 'SUCCESS')
            else:
                self.current_db_path = self.admin_db_path
                if hasattr(self, 'ruta_label'):
                    self.ruta_label.config(text=f"No encontrada - Usando ADMIN")
                self.log_message(f"⚠️ Base de datos no encontrada, usando ADMIN", 'WARNING')
            
        except Exception as e:
            self.log_message(f"❌ Error en selección de año: {str(e)}", 'ERROR')
    
    def buscar_kardex_id(self, codcomp, codprefijo, numero):
        """Busca el Kardex ID en la base de datos específica"""
        conexion = None
        try:
            # Usar la base de datos actual o ADMIN por defecto
            db_a_usar = self.current_db_path if self.current_db_path else self.admin_db_path
            
            conexion = firebirdsql.connect(
                host='localhost',
                database=db_a_usar,
                user='SYSDBA',
                password='masterkey',
                charset='ISO8859_1'
            )
            
            cursor = conexion.cursor()
            
            # Consulta para buscar el Kardex ID
            query = """
                SELECT KARDEXID, CUFE, MENSAJEFE 
                FROM KARDEX 
                WHERE CODCOMP = ? AND CODPREFIJO = ? AND NUMERO = ?
            """
            
            cursor.execute(query, (codcomp, codprefijo, numero))
            resultado = cursor.fetchone()
            
            if resultado:
                kardex_id, cufe, mensajefe = resultado
                self.log_message(f"✅ Kardex encontrado en {os.path.basename(db_a_usar)}: ID={kardex_id}", 'SUCCESS')
                return kardex_id, cufe, mensajefe
            else:
                self.log_message(f"❌ No se encontró Kardex para {codcomp}-{codprefijo}-{numero} en {os.path.basename(db_a_usar)}", 'ERROR')
                return None, None, None
                
        except Exception as e:
            self.log_message(f"❌ Error buscando Kardex: {str(e)}", 'ERROR')
            return None, None, None
        finally:
            if conexion:
                conexion.close()
    
    def buscar_kardex_automaticamente(self):
        """Busca automáticamente el Kardex ID cuando se proporcionan prefijo y número"""
        if not self.prefijo or not self.numero:
            return
        
        self.log_message("🔍 Buscando Kardex automáticamente...", 'INFO')
        
        # Asumimos CODCOMP = "FV" para Factura de Venta
        codcomp = "FV"
        
        kardex_id, cufe, mensajefe = self.buscar_kardex_id(codcomp, self.prefijo, self.numero)
        
        if kardex_id:
            self.kardex_id = kardex_id
            if cufe:
                self.cufe_var.set(cufe)
            self.log_message(f"✅ Kardex ID encontrado: {kardex_id}", 'SUCCESS')
            
            # Actualizar la interfaz con el Kardex ID
            if hasattr(self, 'kardex_label'):
                self.kardex_label.config(text=f"Kardex ID: {kardex_id}")
        else:
            self.log_message("❌ No se pudo encontrar el Kardex", 'ERROR')
    
    def obtener_configuracion(self):
        """Obtiene configuración dinámica de la BD"""
        print("\n🔍 OBTENIENDO CONFIGURACIÓN DINÁMICA")
        
        claves = [
            'TOKENDIANVM', 'ENDPOINTDIANVM', 'GTIPIMPVM', 'GTIPCOTVM',
            'FOOTERDIANVM', 'DIANVMEMAIL', 'DIANVMADDRESS', 'CABECERADIANVM', 'ZESEVM'
        ]
        
        config = {}
        conexion = None
        
        try:
            # Usar la base de datos actual o ADMIN por defecto
            db_a_usar = self.current_db_path if self.current_db_path else self.admin_db_path
            conexion = self.connection_pool.get_connection(db_a_usar)
            cursor = conexion.cursor()
            
            for clave in claves:
                sql = "SELECT CAST(contenido AS VARCHAR(500)) FROM varios WHERE variab = ?"
                try:
                    cursor.execute(sql, (clave,))
                    fila = cursor.fetchone()
                    valor = fila[0] if fila and fila[0] else None
                    config[clave] = valor
                except Exception as e:
                    print(f"❌ Error al obtener '{clave}': {e}")
                    config[clave] = None
            
            print("\n✅ Configuración final obtenida:")
            for k, v in config.items():
                print(f"  {k}: {v}")
                
        except Exception as e:
            print(f"❌ Error general obteniendo configuración: {e}")
            messagebox.showerror("Error", f"No se pudo obtener configuración: {e}")
        finally:
            if conexion:
                self.connection_pool.return_connection(db_a_usar, conexion)
        
        return config
    
    def cargar_configuracion(self):
        """Carga la configuración desde la base de datos"""
        try:
            self.config = self.obtener_configuracion()
            if self.config:
                self.log_message("✅ Configuración cargada exitosamente", 'SUCCESS')
                if self.config.get('ENDPOINTDIANVM'):
                    self.log_message(f"📡 Endpoint: {self.config['ENDPOINTDIANVM']}", 'INFO')
                if self.config.get('TOKENDIANVM'):
                    token_preview = self.config['TOKENDIANVM'][:10] + '...' if len(self.config['TOKENDIANVM']) > 10 else self.config['TOKENDIANVM']
                    self.log_message(f"🔑 Token: {token_preview}", 'INFO')
            else:
                self.log_message("❌ No se pudo cargar la configuración", 'ERROR')
        except Exception as e:
            self.log_message(f"❌ Error cargando configuración: {e}", 'ERROR')
    
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="DIAN Events Manager - Búsqueda Automática", 
                               font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Sección de empresa
        empresa_frame = ttk.LabelFrame(main_frame, text="Selección de Empresa", padding="10")
        empresa_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        empresa_frame.columnconfigure(1, weight=1)
        
        ttk.Label(empresa_frame, text="Empresa:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.empresa_combo = ttk.Combobox(empresa_frame, textvariable=self.empresa_seleccionada,
                                         state="readonly", width=50)
        self.empresa_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.empresa_combo.set("Cargando empresas...")
        self.empresa_combo.bind('<<ComboboxSelected>>', self.on_empresa_seleccionada)
        
        ttk.Label(empresa_frame, text="Año:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.año_combo = ttk.Combobox(empresa_frame, textvariable=self.año_seleccionado,
                                     state="readonly", width=50)
        self.año_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.año_combo.set("Seleccione empresa primero")
        self.año_combo.bind('<<ComboboxSelected>>', self.on_año_seleccionado)
        
        ttk.Label(empresa_frame, text="Base de datos:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.ruta_label = ttk.Label(empresa_frame, text="No seleccionada", foreground="gray")
        self.ruta_label.grid(row=2, column=1, sticky=tk.W)
        
        # Información de parámetros
        params_frame = ttk.LabelFrame(main_frame, text="Información del Documento", padding="10")
        params_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        params_frame.columnconfigure(1, weight=1)
        
        # Búsqueda por prefijo y número
        search_frame = ttk.Frame(params_frame)
        search_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(search_frame, text="Prefijo:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        prefijo_entry = ttk.Entry(search_frame, textvariable=self.prefijo_var, width=15)
        prefijo_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        ttk.Label(search_frame, text="Número:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        numero_entry = ttk.Entry(search_frame, textvariable=self.numero_var, width=15)
        numero_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        ttk.Button(search_frame, text="🔍 Buscar Kardex", 
                  command=self.buscar_kardex_manual).grid(row=0, column=4, padx=(10, 0))
        
        # Información de Kardex
        kardex_frame = ttk.Frame(params_frame)
        kardex_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Label(kardex_frame, text="Kardex ID:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.kardex_label = ttk.Label(kardex_frame, text="No encontrado")
        self.kardex_label.grid(row=0, column=1, sticky=tk.W)
        
        # CUFE
        cufe_frame = ttk.Frame(params_frame)
        cufe_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Label(cufe_frame, text="CUFE:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        cufe_entry = ttk.Entry(cufe_frame, textvariable=self.cufe_var, width=60)
        cufe_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Sección de información del emisor
        issuer_frame = ttk.LabelFrame(main_frame, text="Información del Emisor", padding="10")
        issuer_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        issuer_frame.columnconfigure(1, weight=1)
        
        # Fila 1
        ttk.Label(issuer_frame, text="Número de Identificación:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Entry(issuer_frame, textvariable=self.identification_var).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Label(issuer_frame, text="Nombres:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        ttk.Entry(issuer_frame, textvariable=self.first_name_var).grid(row=0, column=3, sticky=(tk.W, tk.E))
        
        # Fila 2
        ttk.Label(issuer_frame, text="Apellidos:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Entry(issuer_frame, textvariable=self.last_name_var).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Label(issuer_frame, text="Departamento:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10))
        ttk.Entry(issuer_frame, textvariable=self.department_var).grid(row=1, column=3, sticky=(tk.W, tk.E))
        
        # Fila 3
        ttk.Label(issuer_frame, text="Cargo:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Entry(issuer_frame, textvariable=self.job_title_var).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Sección de eventos
        events_frame = ttk.LabelFrame(main_frame, text="Eventos DIAN - Seleccione los eventos a ejecutar", padding="10")
        events_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Crear checkboxes para eventos
        for i, (event_id, event_name) in enumerate(self.events.items()):
            cb = ttk.Checkbutton(events_frame, text=f"{event_id}. {event_name}", 
                                variable=self.event_vars[event_id])
            cb.grid(row=i//2, column=i%2, sticky=tk.W, padx=(0, 20), pady=2)
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=15)
        
        ttk.Button(button_frame, text="🚀 Ejecutar Eventos Seleccionados", 
                  command=self.execute_events, style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="🗑️ Limpiar", 
                  command=self.clear_form).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="🚪 Salir", 
                  command=self.root.quit).pack(side=tk.LEFT)
        
        # Área de logs
        log_frame = ttk.LabelFrame(main_frame, text="Log de Ejecución", padding="10")
        log_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar tags para colores
        self.log_text.tag_config('SUCCESS', foreground='green')
        self.log_text.tag_config('ERROR', foreground='red')
        self.log_text.tag_config('INFO', foreground='blue')
        self.log_text.tag_config('WARNING', foreground='orange')
        self.log_text.tag_config('HEADER', foreground='purple', font=('Arial', 9, 'bold'))
        self.log_text.tag_config('DETAIL', foreground='gray')
        
        # Estilo para botón principal
        style = ttk.Style()
        style.configure('Accent.TButton', foreground='white', background='#d9534f')
        
        self.log_message("✅ Aplicación iniciada correctamente", 'SUCCESS')
        if self.db_path:
            self.log_message(f"📁 Base de datos: {self.db_path}", 'INFO')
        if self.kardex_id:
            self.log_message(f"📋 Kardex ID: {self.kardex_id}", 'INFO')
        if self.prefijo and self.numero:
            self.log_message(f"🔍 Búsqueda automática: {self.prefijo}-{self.numero}", 'INFO')
    
    def buscar_kardex_manual(self):
        """Búsqueda manual de Kardex desde la interfaz"""
        prefijo = self.prefijo_var.get().strip()
        numero = self.numero_var.get().strip()
        
        if not prefijo or not numero:
            messagebox.showerror("Error", "Ingrese prefijo y número")
            return
        
        self.log_message(f"🔍 Buscando Kardex para {prefijo}-{numero}...", 'INFO')
        
        # Asumimos CODCOMP = "FV" para Factura de Venta
        codcomp = "FC"
        
        kardex_id, cufe, mensajefe = self.buscar_kardex_id(codcomp, prefijo, numero)
        
        if kardex_id:
            self.kardex_id = kardex_id
            if cufe:
                self.cufe_var.set(cufe)
            
            # Actualizar la interfaz
            self.kardex_label.config(text=str(kardex_id))
            self.log_message(f"✅ Kardex ID encontrado: {kardex_id}", 'SUCCESS')
        else:
            self.kardex_label.config(text="No encontrado")
            self.log_message("❌ No se pudo encontrar el Kardex", 'ERROR')
    
    def log_message(self, message, level='INFO'):
        """Agrega mensajes al área de logs con timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message, level)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def get_selected_events(self):
        """Obtiene los eventos seleccionados ordenados por ID"""
        selected = []
        for event_id, var in self.event_vars.items():
            if var.get():
                selected.append((event_id, self.events[event_id]))
        # Ordenar por ID
        selected.sort(key=lambda x: x[0])
        return selected
    
    def send_event(self, event_id, event_name):
        """Envía un evento individual a la DIAN usando configuración de BD"""
        if not self.config:
            self.log_message("❌ Configuración no disponible", 'ERROR')
            return False, "Configuración no disponible"
        
        endpoint_base = self.config.get('ENDPOINTDIANVM')
        token = self.config.get('TOKENDIANVM')
        
        if not endpoint_base or not token:
            self.log_message("❌ Endpoint o Token no configurado", 'ERROR')
            return False, "Endpoint o Token no configurado"
        
        # CORREGIR: Limpiar la URL base y construir endpoint correcto
        # Eliminar slash final si existe
        endpoint_base = endpoint_base.rstrip('/')
        # Construir endpoint completo CORREGIDO
        endpoint = f"{endpoint_base}/send-event-data"
        
        self.log_message(f"🔍 URL construida: {endpoint}", 'DETAIL')
        
        payload = json.dumps({
            "event_id": str(event_id),
            "document_reference": {
                "cufe": self.cufe_var.get().strip()
            },
            "issuer_party": {
                "identification_number": self.identification_var.get().strip(),
                "first_name": self.first_name_var.get().strip(),
                "last_name": self.last_name_var.get().strip(),
                "organization_department": self.department_var.get().strip(),
                "job_title": self.job_title_var.get().strip()
            }
        })
        
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        try:
            self.log_message(f"🔄 Enviando evento {event_id}: {event_name}...")
            self.log_message(f"   📡 Endpoint: {endpoint}", 'DETAIL')
            self.log_message(f"   🔑 Token (con Bearer): Bearer {token[:20]}...", 'DETAIL')
            self.log_message(f"   📦 Payload: {payload}", 'DETAIL')
            
            response = requests.post(endpoint, headers=headers, data=payload, timeout=60)
            
            # Mostrar respuesta completa sin importar el resultado
            self.log_message(f"   📊 Código HTTP: {response.status_code}", 'DETAIL')
            
            try:
                response_data = response.json()
            except:
                self.log_message(f"   ❌ Respuesta no es JSON: {response.text}", 'ERROR')
                return False, f"Respuesta no es JSON: {response.text}"
            
            # Mostrar TODA la respuesta en el log
            self.log_message("   📋 RESPUESTA COMPLETA:", 'INFO')
            self.log_message(f"   {json.dumps(response_data, indent=2, ensure_ascii=False)}", 'DETAIL')
            
            # Verificar si fue exitoso
            if response_data.get('success'):
                self.log_message(f"✅ Evento {event_id} exitoso", 'SUCCESS')
                
                # Capturar información específica
                if 'cude' in response_data:
                    self.log_message(f"   🔑 CUDE: {response_data['cude']}", 'SUCCESS')
                
                if 'certificate_days_left' in response_data:
                    self.log_message(f"   📅 Días restantes certificado: {response_data['certificate_days_left']}", 'INFO')
                
                # Mostrar información de ResponseDian si existe
                if 'ResponseDian' in response_data:
                    result = response_data['ResponseDian']['Envelope']['Body']['SendEventUpdateStatusResponse']['SendEventUpdateStatusResult']
                    status_desc = result.get('StatusDescription', 'N/A')
                    self.log_message(f"   🏛️ Estado DIAN: {status_desc}", 'INFO')
                    
                return True, response_data.get('message', 'Éxito')
            else:
                self.log_message(f"❌ Evento {event_id} falló", 'ERROR')
                error_msg = response_data.get('message', 'Error desconocido')
                self.log_message(f"   💬 Error: {error_msg}", 'ERROR')
                
                # Mostrar errores de validación DIAN si existen
                if 'ResponseDian' in response_data:
                    result = response_data['ResponseDian']['Envelope']['Body']['SendEventUpdateStatusResponse']['SendEventUpdateStatusResult']
                    error_msg_dian = result.get('ErrorMessage', {}).get('string', '')
                    if error_msg_dian:
                        self.log_message(f"   🚫 Error DIAN: {error_msg_dian}", 'ERROR')
                
                return False, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión: {str(e)}"
            self.log_message(f"❌ {error_msg}", 'ERROR')
            return False, error_msg
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            self.log_message(f"❌ {error_msg}", 'ERROR')
            return False, error_msg
    
    def update_kardex(self, success, error_message=None):
        """Actualiza el Kardex en la base de datos usando MENSAJEFE"""
        if not self.kardex_id:
            return True
        
        conexion = None
        try:
            # Usar la base de datos actual para actualizar
            db_a_usar = self.current_db_path if self.current_db_path else self.admin_db_path
            
            conexion = firebirdsql.connect(
                host='localhost',
                database=db_a_usar,
                user='SYSDBA',
                password='masterkey',
                charset='ISO8859_1'
            )
                
            cursor = conexion.cursor()
            
            if success:
                # Todos los eventos exitosos - actualizar CUFE y REVISADO
                sql = "UPDATE KARDEX SET CUFE = ?, REVISADO = 'S' WHERE KARDEXID = ?"
                cursor.execute(sql, (self.cufe_var.get().strip(), self.kardex_id))
                self.log_message(f"✅ Kardex actualizado - CUFE: {self.cufe_var.get().strip()}, REVISADO: 'S'", 'SUCCESS')
            else:
                # Hubo errores - actualizar mensaje de error en MENSAJEFE
                sql = "UPDATE KARDEX SET MENSAJEFE = ? WHERE KARDEXID = ?"
                error_msg = error_message or "ERRORES en eventos DIAN"
                cursor.execute(sql, (error_msg, self.kardex_id))
                self.log_message(f"⚠️ Kardex actualizado - MENSAJEFE: {error_msg}", 'WARNING')
            
            conexion.commit()
            return True
            
        except Exception as e:
            self.log_message(f"❌ Error actualizando Kardex: {str(e)}", 'ERROR')
            if conexion:
                conexion.rollback()
            return False
        finally:
            if conexion:
                conexion.close()
    
    def execute_events(self):
        """Ejecuta los eventos seleccionados en orden"""
        # Validaciones
        if not self.cufe_var.get().strip():
            messagebox.showerror("Error", "Por favor ingrese el CUFE")
            return
        
        selected_events = self.get_selected_events()
        if not selected_events:
            messagebox.showwarning("Advertencia", "Por favor seleccione al menos un evento")
            return
        
        # Confirmación
        confirm = messagebox.askyesno(
            "Confirmar Ejecución", 
            f"¿Está seguro de ejecutar {len(selected_events)} evento(s) seleccionados?\n\n" +
            "\n".join([f"{id}: {name}" for id, name in selected_events])
        )
        
        if not confirm:
            return
        
        # Ejecutar en un hilo separado para no bloquear la UI
        thread = threading.Thread(target=self._execute_events_thread, args=(selected_events,))
        thread.daemon = True
        thread.start()
    
    def _execute_events_thread(self, selected_events):
        """Ejecuta los eventos en un hilo separado de manera SECUENCIAL"""
        self.log_message("=" * 60, 'HEADER')
        self.log_message("🚀 INICIANDO EJECUCIÓN SECUENCIAL DE EVENTOS", 'HEADER')
        self.log_message("=" * 60, 'HEADER')
        
        total_events = len(selected_events)
        success_count = 0
        error_messages = []
        
        # Ejecutar eventos SECUENCIALMENTE
        for i, (event_id, event_name) in enumerate(selected_events, 1):
            self.log_message(f"📦 Procesando evento {i} de {total_events}: {event_name} (ID: {event_id})", 'INFO')
            
            # Ejecutar evento y esperar respuesta
            success, message = self.send_event(event_id, event_name)
            
            if success:
                success_count += 1
                self.log_message(f"✅ Evento {event_id} COMPLETADO EXITOSAMENTE", 'SUCCESS')
            else:
                error_messages.append(f"Evento {event_id}: {message}")
                self.log_message(f"❌ Evento {event_id} FALLÓ", 'ERROR')
            
            # Pequeña pausa entre eventos (excepto el último)
            if i < total_events:
                self.log_message("⏳ Esperando 2 segundos antes del próximo evento...", 'INFO')
                threading.Event().wait(2)
        
        # Actualizar Kardex si se proporcionó ID
        kardex_updated = False
        if self.kardex_id:
            all_success = (success_count == total_events)
            error_message = "; ".join(error_messages) if error_messages else None
            kardex_updated = self.update_kardex(all_success, error_message)
        
        self.log_message("=" * 60, 'HEADER')
        self.log_message(f"🏁 EJECUCIÓN COMPLETADA - {success_count}/{total_events} exitosos", 
                        'SUCCESS' if success_count == total_events else 'WARNING')
        
        if self.kardex_id:
            status = "✅ ACTUALIZADO" if kardex_updated else "❌ NO ACTUALIZADO"
            self.log_message(f"📋 KARDEX: {status}", 'SUCCESS' if kardex_updated else 'ERROR')
        
        self.log_message("=" * 60, 'HEADER')
        
        # Mostrar mensaje final
        if success_count == total_events:
            messagebox.showinfo("Éxito", f"Todos los {total_events} eventos se ejecutaron exitosamente")
        else:
            messagebox.showwarning("Completado", 
                                 f"Ejecución completada. {success_count} de {total_events} eventos exitosos")
    
    def clear_form(self):
        """Limpia el formulario"""
        self.cufe_var.set("")
        self.prefijo_var.set("")
        self.numero_var.set("")
        self.kardex_label.config(text="No encontrado")
        for var in self.event_vars.values():
            var.set(False)
        self.log_text.delete(1.0, tk.END)

def main():
    # Verificar parámetros - ahora más flexible
    if len(sys.argv) < 3:
        print("Uso:")
        print("  evento.exe [RUTA_GDB] [IDENTIFICATION] [FIRST_NAME] [LAST_NAME] [DEPARTMENT] [JOB_TITLE] [PREFIJO] [NUMERO]")
        print("\nEjemplos:")
        print('  evento.exe "C:\\Datos TNS\\CGR INV 2025V2.GDB" "13279115" "VICTOR" "RINCON" "SISTEMAS" "ING SISTEMAS"')
        print('  evento.exe "" "13279115" "VICTOR" "RINCON" "SISTEMAS" "ING SISTEMAS" "FV001" "12345"')
        print('\nNota: Si no se proporcionan parámetros, se usará ADMIN.GDB y modo interactivo')
        
        # Si no hay suficientes parámetros, crear app con valores por defecto
        db_path = sys.argv[1] if len(sys.argv) > 1 else None
        identification = sys.argv[2] if len(sys.argv) > 2 else "13279115"
        first_name = sys.argv[3] if len(sys.argv) > 3 else "VICTOR"
        last_name = sys.argv[4] if len(sys.argv) > 4 else "RINCON"
        department = sys.argv[5] if len(sys.argv) > 5 else "SISTEMAS"
        job_title = sys.argv[6] if len(sys.argv) > 6 else "ING SISTEMAS"
        prefijo = sys.argv[7] if len(sys.argv) > 7 else None
        numero = sys.argv[8] if len(sys.argv) > 8 else None
    else:
        # Obtener parámetros de línea de comandos
        db_path = sys.argv[1] if sys.argv[1] else None
        identification = sys.argv[2]
        first_name = sys.argv[3]
        last_name = sys.argv[4]
        department = sys.argv[5]
        job_title = sys.argv[6] if len(sys.argv) > 6 else ""
        prefijo = sys.argv[7] if len(sys.argv) > 7 else None
        numero = sys.argv[8] if len(sys.argv) > 8 else None
    
    # Mostrar parámetros recibidos
    print(f"📁 Base de datos: {db_path or 'ADMIN (automática)'}")
    print(f"👤 Identificación: {identification}")
    print(f"👤 Nombres: {first_name}")
    print(f"👤 Apellidos: {last_name}")
    print(f"🏢 Departamento: {department}")
    print(f"💼 Cargo: {job_title}")
    if prefijo and numero:
        print(f"🔍 Búsqueda: {prefijo}-{numero}")
    
    # Crear y ejecutar aplicación
    root = tk.Tk()
    app = DianEventsApp(root, db_path, identification, first_name, last_name, 
                       department, job_title, None, prefijo, numero)
    root.mainloop()

if __name__ == "__main__":
    main()