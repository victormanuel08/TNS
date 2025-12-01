# sistema_analitico/services/data_manager.py
import pandas as pd
import pickle
import os
from datetime import datetime
from django.conf import settings
from django.utils import timezone
import logging

from ..models import Servidor, EmpresaServidor, MovimientoInventario
from .database_connectors import DatabaseConnector

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self):
        self.maestro_path = os.path.join(settings.BASE_DIR, 'data/maestro.pkl')
        self.cache_dir = os.path.join(settings.BASE_DIR, 'data/cache/')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.connector = DatabaseConnector()
    
    def inicializar_sistema(self):
        if os.path.exists(self.maestro_path):
            return self.cargar_maestro()
        else:
            return self.crear_maestro_inicial()
    
    def crear_maestro_inicial(self):
        maestro = {
            'version': '2.0',
            'fecha_creacion': datetime.now().isoformat(),
            'ultima_actualizacion': datetime.now().isoformat(),
            'servidores': {},
            'empresas': {},
            'configuracion': {
                'retencion_datos': 365,
                'actualizacion_automatica': True,
            }
        }
        self.guardar_maestro(maestro)
        return maestro
    
    def cargar_maestro(self):
        with open(self.maestro_path, 'rb') as f:
            return pickle.load(f)
    
    def guardar_maestro(self, maestro):
        maestro['ultima_actualizacion'] = datetime.now().isoformat()
        with open(self.maestro_path, 'wb') as f:
            pickle.dump(maestro, f)
    
    def registrar_servidor(self, nombre, host, usuario, password, tipo_servidor, puerto=None):
        servidor = Servidor.objects.create(
            nombre=nombre, host=host, usuario=usuario, password=password,
            tipo_servidor=tipo_servidor, puerto=puerto or self._puerto_por_defecto(tipo_servidor)
        )
        
        maestro = self.cargar_maestro()
        maestro['servidores'][str(servidor.id)] = {
            'nombre': servidor.nombre, 'host': servidor.host, 'tipo': servidor.tipo_servidor
        }
        self.guardar_maestro(maestro)
        return servidor
    
    def descubrir_empresas(self, servidor_id):
        servidor = Servidor.objects.get(id=servidor_id)
        
        # Validar que la ruta maestra esté configurada
        if not servidor.ruta_maestra:
            raise ValueError(f"El servidor '{servidor.nombre}' no tiene configurada la ruta maestra. Por favor, edita el servidor y agrega la ruta a la base de datos maestra (ej: C:\\datos\\ADMIN.gdb o /ruta/al/ADMIN.gdb)")
        
        try:
            logger.info(f"Intentando conectar a servidor: {servidor.nombre} ({servidor.tipo_servidor}) - {servidor.host}:{servidor.puerto or 'default'}")
            conexion = self._conectar_servidor_base(servidor)
            logger.info(f"Conexión exitosa al servidor {servidor.nombre}")
            
            consulta_empresas = "SELECT CODIGO, NOMBRE, NIT, ANOFIS, ARCHIVO FROM EMPRESAS WHERE NIT IS NOT NULL ORDER BY NIT, ANOFIS"
            
            df_empresas = self.connector.ejecutar_consulta(
                conexion, consulta_empresas, tipo_servidor=servidor.tipo_servidor
            )
            
            empresas_registradas = []
            for _, fila in df_empresas.iterrows():
                nit = fila['NIT']
                anio_fiscal = fila['ANOFIS']
                
                # Verificar si ya existe una empresa con este NIT y año fiscal en otro servidor
                empresa_existente = EmpresaServidor.objects.filter(
                    nit=nit, anio_fiscal=anio_fiscal
                ).exclude(servidor=servidor).first()
                
                if empresa_existente:
                    empresas_registradas.append({
                        'empresa': fila['NOMBRE'], 'nit': nit, 
                        'anio_fiscal': anio_fiscal, 
                        'accion': 'omitida',
                        'razon': f'Ya existe en servidor "{empresa_existente.servidor.nombre}"'
                    })
                    continue
                
                # Si existe en el mismo servidor, actualizar; si no, crear
                empresa, creada = EmpresaServidor.objects.update_or_create(
                    servidor=servidor, nit=nit, anio_fiscal=anio_fiscal,
                    defaults={
                        'codigo': fila['CODIGO'], 'nombre': fila['NOMBRE'],
                        'ruta_base': fila['ARCHIVO'], 'estado': 'ACTIVO'
                    }
                )
                empresas_registradas.append({
                    'empresa': empresa.nombre, 'nit': empresa.nit, 
                    'anio_fiscal': empresa.anio_fiscal, 'accion': 'creada' if creada else 'actualizada'
                })
            
            if hasattr(conexion, 'close'):
                conexion.close()
            
            return empresas_registradas
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error descubriendo empresas en servidor {servidor.nombre}: {error_msg}")
            
            # Mensajes de error más descriptivos
            if '10060' in error_msg or 'timeout' in error_msg.lower():
                raise Exception(
                    f"No se pudo conectar al servidor '{servidor.nombre}' ({servidor.host}:{servidor.puerto or 'default'}).\n\n"
                    f"Posibles causas:\n"
                    f"• El servidor Firebird no está corriendo en {servidor.host}\n"
                    f"• La IP {servidor.host} no es accesible desde esta máquina\n"
                    f"• El puerto {servidor.puerto or 3050} está bloqueado por firewall\n"
                    f"• La ruta maestra '{servidor.ruta_maestra}' no existe o es incorrecta\n\n"
                    f"Verifica:\n"
                    f"1. Que el servidor Firebird esté corriendo en {servidor.host}\n"
                    f"2. Que puedas hacer ping a {servidor.host}\n"
                    f"3. Que el puerto {servidor.puerto or 3050} esté abierto\n"
                    f"4. Que la ruta maestra sea correcta"
                )
            elif '10061' in error_msg or 'connection refused' in error_msg.lower():
                raise Exception(
                    f"La conexión fue rechazada por el servidor '{servidor.nombre}' ({servidor.host}:{servidor.puerto or 'default'}).\n\n"
                    f"El servidor está accesible pero rechazó la conexión. Verifica:\n"
                    f"• Que Firebird esté corriendo en el puerto {servidor.puerto or 3050}\n"
                    f"• Que las credenciales (usuario/password) sean correctas\n"
                    f"• Que el usuario tenga permisos para acceder a la base de datos"
                )
            else:
                raise Exception(f"Error conectando al servidor '{servidor.nombre}': {error_msg}")
    
    def extraer_datos_empresa(self, empresa_servidor_id, fecha_inicio, fecha_fin, forzar_reextraccion=False):
        emp_serv = EmpresaServidor.objects.get(id=empresa_servidor_id)
        servidor = emp_serv.servidor

        print(f"🔍 EMPRESA: {emp_serv.nombre}")

        if not forzar_reextraccion and self._ya_extraido(emp_serv, fecha_inicio, fecha_fin):
            return {"estado": "ya_extraido", "mensaje": f"Datos ya extraídos para {fecha_inicio} a {fecha_fin}"}

        try:
            
            total_registros = self._contar_registros(emp_serv, servidor, fecha_inicio, fecha_fin)
            print(f"📊 TOTAL REGISTROS: {total_registros}")

            if total_registros == 0:
                return {"estado": "sin_datos", "registros": 0}

            
            chunk_size = 1000
            total_chunks = (total_registros + chunk_size - 1) // chunk_size 

            print(f"🔢 EXTRACCIÓN EN {total_chunks} CHUNKS DE {chunk_size} REGISTROS")

            total_guardados = 0

            
            for chunk_num in range(total_chunks):
                offset = chunk_num * chunk_size
                print(f"📦 CHUNK {chunk_num + 1}/{total_chunks} (offset: {offset})")

                resultado_chunk = self._extraer_chunk(
                    emp_serv, servidor, fecha_inicio, fecha_fin, offset, chunk_size
                )

                if resultado_chunk.get('estado') == 'error':
                    return resultado_chunk

                registros_chunk = resultado_chunk.get('registros_guardados', 0)
                total_guardados += registros_chunk
                print(f"✅ CHUNK {chunk_num + 1}: {registros_chunk} registros")

                
                import time
                time.sleep(0.1)

            emp_serv.ultima_extraccion = timezone.now()
            emp_serv.save()

            return {
                "estado": "exito", 
                "registros_guardados": total_guardados,
                "total_encontrados": total_registros,
                "chunks_procesados": total_chunks
            }

        except Exception as e:
            print(f"❌ ERROR EN EXTRACCIÓN: {e}")
            return {"estado": "error", "error": str(e)}

    def _contar_registros(self, emp_serv, servidor, fecha_inicio, fecha_fin):
        """Cuenta total de registros con la consulta original + WHERE"""
        try:
            conexion = self._conectar_servidor_empresa(servidor, emp_serv.ruta_base)

           
            consulta_original = emp_serv.consulta_sql
            consulta_count = self._convertir_a_count(consulta_original)

            cursor = conexion.cursor()
            cursor.execute(consulta_count, [fecha_inicio, fecha_fin])
            resultado = cursor.fetchone()
            cursor.close()
            conexion.close()

            return resultado[0] if resultado else 0

        except Exception as e:
            print(f"❌ ERROR EN COUNT: {e}")
            return 0

    def _convertir_a_count(self, consulta_sql):
        """Convierte SELECT ... a SELECT COUNT(*) manteniendo FROM y WHERE"""
        
        from_pos = consulta_sql.upper().find('FROM')
        if from_pos == -1:
            raise ValueError("Consulta SQL no tiene FROM")

       
        return f"SELECT COUNT(*) {consulta_sql[from_pos:]}"

    def _extraer_chunk(self, emp_serv, servidor, fecha_inicio, fecha_fin, offset, limit):
        """Extrae un chunk específico usando ROWS de Firebird"""
        try:
            conexion = self._conectar_servidor_empresa(servidor, emp_serv.ruta_base)

           
            consulta_original = emp_serv.consulta_sql
            consulta_chunk = self._agregar_filas(consulta_original, offset, limit)

            df = self.connector.ejecutar_consulta(
                conexion, consulta_chunk,
                params=[fecha_inicio, fecha_fin],
                tipo_servidor=servidor.tipo_servidor,
                chunk_size=500
            )

            if hasattr(conexion, 'close'):
                conexion.close()

            if df.empty:
                return {"estado": "sin_datos", "registros": 0}

            registros_guardados = self._guardar_movimientos(df, emp_serv)
            return {"estado": "exito", "registros_guardados": registros_guardados}

        except Exception as e:
            print(f"❌ ERROR EN CHUNK {offset}: {e}")
            return {"estado": "error", "error": str(e)}

    def _agregar_filas(self, consulta_sql, offset, limit):
        """Agrega cláusula ROWS para Firebird (ROWS X TO Y)"""
        return f"{consulta_sql} ROWS {offset + 1} TO {offset + limit}"
    
    def _conectar_servidor_empresa(self, servidor, ruta_base):
        if servidor.tipo_servidor == 'FIREBIRD':
            return self.connector.conectar_firebird(servidor, ruta_base)
        elif servidor.tipo_servidor == 'POSTGRESQL':
            return self.connector.conectar_postgresql(servidor, ruta_base)
        elif servidor.tipo_servidor == 'SQLSERVER':
            return self.connector.conectar_sqlserver(servidor, ruta_base)
        else:
            raise ValueError(f"Tipo de servidor no soportado: {servidor.tipo_servidor}")
    
    def _conectar_servidor_base(self, servidor):
        """Conecta al servidor usando la ruta maestra"""
        return self._conectar_servidor_empresa(servidor, servidor.ruta_maestra)
    
    def _ya_extraido(self, empresa_servidor, fecha_inicio, fecha_fin):
        return MovimientoInventario.objects.filter(
            empresa_servidor=empresa_servidor, fecha__gte=fecha_inicio, fecha__lte=fecha_fin
        ).exists()
    
    def _guardar_movimientos(self, df, empresa_servidor):
        print(f"🔄 PROCESANDO {len(df)} FILAS")

       
        columnas_requeridas = ['TIPO_DOCUMENTO', 'FECHA', 'ARTICULO_CODIGO', 'ARTICULO_NOMBRE', 'CANTIDAD']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]

        if columnas_faltantes:
            print(f"❌ COLUMNAS FALTANTES: {columnas_faltantes}")
            return 0

        movimientos = []
        print(f"Procesando {len(df)} filas para la empresa {empresa_servidor.nombre}...")
        for _, fila in df.iterrows():
          
            nit_pagador = self._limpiar_nit(fila.get('NIT_PAGADOR'))
            nit_clinica = self._limpiar_nit(fila.get('NIT_CLINICA'))

            movimiento = MovimientoInventario(
                empresa_servidor=empresa_servidor,
                tipo_documento=self._mapear_tipo_documento(fila.get('TIPO_DOCUMENTO')),
                fecha=self._parsear_fecha(fila.get('FECHA')),
                fecha_orden_pedido=self._parsear_fecha(fila.get('FECHA_ORDEN_PEDIDO')),

              
                paciente=fila.get('PACIENTE'),
                cedula_paciente=fila.get('CEDULA_PACIENTE'),

               
                pagador=fila.get('PAGADOR'),
                nit_pagador=nit_pagador,

               
                clinica=fila.get('CLINICA'),
                nit_clinica=nit_clinica,

             
                medico=fila.get('MEDICO'),
                cedula_medico=fila.get('CEDULA_MEDICO'),
                medico2=fila.get('MEDICO2'),
                cedula_medico2=fila.get('CEDULA_MEDICO2'),

                procedimientos=fila.get('PROCEDIMIENTOS'),

              
                codigo_ciudad=fila.get('CODIGO_CIUDAD'),
                ciudad=fila.get('CIUDAD'),

               
                tipo_bodega=fila.get('TIPO_BODEGA'),
                codigo_bodega=fila.get('CODIGO_BODEGA'),
                sistema_bodega=fila.get('SISTEMA_BODEGA'),
                bodega_contenedor=fila.get('BODEGA_CONTENEDOR'),

               
                articulo_nombre=fila.get('ARTICULO_NOMBRE'),
                articulo_codigo=fila.get('ARTICULO_CODIGO'),
                cantidad=fila.get('CANTIDAD', 0),
                precio_unitario=fila.get('PRECIO_UNITARIO', 0),
                lote=fila.get('LOTE'),
                stock_previo=fila.get('STOCK_PREVIO'),
                stock_nuevo=fila.get('STOCK_NUEVO')
            )

            
            movimiento.valor_total = movimiento.cantidad * movimiento.precio_unitario

            if movimiento.fecha and movimiento.fecha_orden_pedido:
                movimiento.lead_time_dias = (movimiento.fecha - movimiento.fecha_orden_pedido).days

            # Calcular booleanos de tipo de bodega basado en TIPO_BODEGA del SQL
            # El SQL ya calcula: 'IMPLANTE', 'EQUIPO DE PODER', o 'INSTRUMENTAL'
            if movimiento.tipo_bodega:
                tipo_bodega = str(movimiento.tipo_bodega).upper().strip()
                movimiento.es_implante = tipo_bodega == 'IMPLANTE'
                movimiento.es_instrumental = tipo_bodega == 'INSTRUMENTAL'
                movimiento.es_equipo_poder = tipo_bodega == 'EQUIPO DE PODER'
            else:
                # Si no hay tipo_bodega, usar valores por defecto
                movimiento.es_implante = False
                movimiento.es_instrumental = False
                movimiento.es_equipo_poder = False

            movimientos.append(movimiento)

        print(f"Guardando {len(movimientos)} movimientos para la empresa {empresa_servidor.nombre}...")
        MovimientoInventario.objects.bulk_create(movimientos, batch_size=1000)
        return len(movimientos)

    def _limpiar_nit(self, nit):
        """Elimina todo después del guión incluyendo el guión"""
        if nit and '-' in str(nit):
            return str(nit).split('-')[0].strip()
        return nit

    def _mapear_tipo_documento(self, tipo_doc):
        mapeo = {
            'FV': 'FACTURA_VENTA',
            'FC': 'FACTURA_COMPRA', 
            'DV': 'DEVOLUCION_VENTA',
            'DC': 'DEVOLUCION_COMPRA',
            'RE': 'REMISION_ENTRADA',
        }
        return mapeo.get(str(tipo_doc).strip().upper(), 'FACTURA_VENTA')   
    
    def _parsear_fecha(self, fecha):
        if pd.isna(fecha) or fecha is None:
            return None
        if isinstance(fecha, str):
          
            dt_naive = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
            return timezone.make_aware(dt_naive)
        elif isinstance(fecha, datetime):
          
            if timezone.is_naive(fecha):
                return timezone.make_aware(fecha)
            return fecha
        return fecha
    
    def _puerto_por_defecto(self, tipo_servidor):
        puertos = {'FIREBIRD': 3050, 'POSTGRESQL': 5432, 'SQLSERVER': 1433, 'MYSQL': 3306}
        return puertos.get(tipo_servidor, 0)