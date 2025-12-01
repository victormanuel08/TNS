"""
Módulo SQLite para reemplazar Excel en makos.py
GARANTIZA: Misma interfaz, misma lógica, solo cambia el almacenamiento
NO MODIFICA: Inserción Firebird, validaciones, terceros, materiales, correo
"""
import sqlite3
import pandas as pd
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import threading

class MakosDatabase:
    """
    Clase que reemplaza Excel con SQLite manteniendo EXACTAMENTE la misma interfaz
    self.df sigue siendo un DataFrame para que todo el código existente funcione igual
    """
    
    def __init__(self, db_path=None, log_callback=None):
        """
        Inicializa la base de datos SQLite
        
        Args:
            db_path: Ruta al archivo SQLite (default: Facturas_Makos.db en mismo directorio)
            log_callback: Función para logging (opcional)
        """
        if db_path is None:
            # Usar mismo directorio que el script o .exe
            # Si está compilado como .exe, usar el directorio del .exe
            # Si es script, usar el directorio del script
            if getattr(sys, 'frozen', False):
                # Compilado como .exe
                base_dir = Path(sys.executable).parent
            else:
                # Ejecutado como script
                base_dir = Path(__file__).parent
            db_path = base_dir / "Facturas_Makos.db"
        
        self.db_path = str(db_path)
        self.log = log_callback or (lambda msg: print(msg))
        self._lock = threading.Lock()  # Lock para operaciones de escritura
        
        # Crear conexión y tablas
        self._inicializar_db()
    
    def _inicializar_db(self):
        """Crea las tablas necesarias si no existen"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging para mejor concurrencia
        conn.execute("PRAGMA foreign_keys=ON")
        
        cursor = conn.cursor()
        
        # Tabla principal de facturas (equivalente al Excel)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prefijo TEXT NOT NULL,
                numero TEXT NOT NULL,
                fecha TEXT NOT NULL,
                cliente TEXT,
                total REAL DEFAULT 0,
                subtotal_makos REAL DEFAULT 0,
                impuestos_makos REAL DEFAULT 0,
                propina_makos REAL DEFAULT 0,
                estado TEXT DEFAULT 'PENDIENTE_TNS',
                tns TEXT DEFAULT 'NO',
                validacion TEXT DEFAULT 'PENDIENTE',
                validacion_impuestos TEXT DEFAULT 'PENDIENTE',
                diferencia_impuestos REAL DEFAULT 0,
                kardexid TEXT,
                prefijo_tns TEXT,
                numero_tns TEXT,
                total_tns REAL DEFAULT 0,
                neto_base_tns REAL DEFAULT 0,
                iva_tns REAL DEFAULT 0,
                imp_consumo_tns REAL DEFAULT 0,
                telefono TEXT,
                ubicacion TEXT,
                detalles TEXT,  -- JSON string
                checked TEXT DEFAULT '',
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(prefijo, numero)
            )
        """)
        
        # Índices para búsquedas rápidas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prefijo_numero ON facturas(prefijo, numero)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fecha ON facturas(fecha)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estado ON facturas(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tns ON facturas(tns)")
        
        conn.commit()
        conn.close()
        
        self.log(f"✅ Base de datos SQLite inicializada: {self.db_path}")
    
    def cargar_facturas(self, columnas_requeridas):
        """
        Carga facturas desde SQLite y retorna un DataFrame
        MANTIENE EXACTAMENTE la misma interfaz que cargar_facturas() original
        
        Args:
            columnas_requeridas: Lista de columnas requeridas (para compatibilidad)
        
        Returns:
            pd.DataFrame: DataFrame con las facturas cargadas
        """
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                
                # Cargar todas las facturas
                query = """
                    SELECT 
                        prefijo AS 'Prefijo',
                        numero AS 'Número',
                        fecha AS 'Fecha',
                        cliente AS 'Cliente',
                        total AS 'Total',
                        subtotal_makos AS 'SubtotalMakos',
                        impuestos_makos AS 'ImpuestosMakos',
                        propina_makos AS 'PropinaMakos',
                        estado AS 'Estado',
                        tns AS 'TNS',
                        validacion AS 'Validacion',
                        validacion_impuestos AS 'ValidacionImpuestos',
                        diferencia_impuestos AS 'DiferenciaImpuestos',
                        kardexid AS 'KARDEXID',
                        prefijo_tns AS 'PrefijoTNS',
                        numero_tns AS 'NumeroTNS',
                        total_tns AS 'TotalTNS',
                        neto_base_tns AS 'NetoBaseTNS',
                        iva_tns AS 'IvaTNS',
                        imp_consumo_tns AS 'ImpConsumoTNS',
                        telefono AS 'Teléfono',
                        ubicacion AS 'Ubicación',
                        detalles AS 'Detalles',
                        checked AS 'Checked'
                    FROM facturas
                    ORDER BY fecha DESC
                """
                
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                # ✅ ASEGURAR QUE EXISTAN TODAS LAS COLUMNAS REQUERIDAS (igual que Excel)
                for columna in columnas_requeridas:
                    if columna not in df.columns:
                        if any(x in columna for x in ['Total', 'Subtotal', 'Impuestos', 'Propina', 'Base', 'IVA', 'Consumo', 'Diferencia']):
                            df[columna] = 0.0
                        else:
                            df[columna] = ''
                
                # Convertir fecha a datetime (igual que Excel)
                if 'Fecha' in df.columns and not df.empty:
                    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
                    df = df.sort_values('Fecha', ascending=False)
                
                # Eliminar duplicados (igual que Excel)
                if not df.empty:
                    df = df.drop_duplicates(subset=['Prefijo', 'Número'], keep='last')
                
                self.log(f"📊 SQLite cargado - {len(df)} registros únicos")
                return df
                
        except Exception as e:
            self.log(f"❌ Error al cargar desde SQLite: {str(e)}")
            # Retornar DataFrame vacío con columnas requeridas (igual que Excel)
            return pd.DataFrame(columns=columnas_requeridas)
    
    def guardar_facturas(self, df):
        """
        Guarda el DataFrame en SQLite
        MANTIENE EXACTAMENTE la misma interfaz que guardar_excel() original
        
        Args:
            df: DataFrame de pandas con las facturas
        
        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        try:
            if df is None or df.empty:
                self.log("⚠️ No hay datos para guardar")
                return False
            
            with self._lock:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.execute("PRAGMA synchronous = NORMAL")  # Más rápido que FULL
                conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
                cursor = conn.cursor()
                
                # ✅ OPTIMIZACIÓN: Preparar datos en lote (MUCHO MÁS RÁPIDO que iterrows)
                datos = []
                for _, row in df.iterrows():
                    try:
                        # Convertir fecha a string si es datetime
                        fecha_str = row.get('Fecha', '')
                        if hasattr(fecha_str, 'strftime'):
                            fecha_str = fecha_str.strftime('%Y-%m-%d %H:%M:%S')
                        elif pd.isna(fecha_str):
                            fecha_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            fecha_str = str(fecha_str)
                        
                        # Convertir Detalles a JSON string si es dict
                        detalles_str = row.get('Detalles', '')
                        if isinstance(detalles_str, dict):
                            detalles_str = json.dumps(detalles_str, ensure_ascii=False)
                        elif pd.isna(detalles_str):
                            detalles_str = ''
                        else:
                            detalles_str = str(detalles_str)
                        
                        datos.append((
                            str(row.get('Prefijo', '')),
                            str(row.get('Número', '')),
                            fecha_str,
                            str(row.get('Cliente', '')),
                            float(row.get('Total', 0)) if pd.notna(row.get('Total')) else 0.0,
                            float(row.get('SubtotalMakos', 0)) if pd.notna(row.get('SubtotalMakos')) else 0.0,
                            float(row.get('ImpuestosMakos', 0)) if pd.notna(row.get('ImpuestosMakos')) else 0.0,
                            float(row.get('PropinaMakos', 0)) if pd.notna(row.get('PropinaMakos')) else 0.0,
                            str(row.get('Estado', 'PENDIENTE_TNS')),
                            str(row.get('TNS', 'NO')),
                            str(row.get('Validacion', 'PENDIENTE')),
                            str(row.get('ValidacionImpuestos', 'PENDIENTE')),
                            float(row.get('DiferenciaImpuestos', 0)) if pd.notna(row.get('DiferenciaImpuestos')) else 0.0,
                            str(row.get('KARDEXID', '')) if pd.notna(row.get('KARDEXID')) else '',
                            str(row.get('PrefijoTNS', '')) if pd.notna(row.get('PrefijoTNS')) else '',
                            str(row.get('NumeroTNS', '')) if pd.notna(row.get('NumeroTNS')) else '',
                            float(row.get('TotalTNS', 0)) if pd.notna(row.get('TotalTNS')) else 0.0,
                            float(row.get('NetoBaseTNS', 0)) if pd.notna(row.get('NetoBaseTNS')) else 0.0,
                            float(row.get('IvaTNS', 0)) if pd.notna(row.get('IvaTNS')) else 0.0,
                            float(row.get('ImpConsumoTNS', 0)) if pd.notna(row.get('ImpConsumoTNS')) else 0.0,
                            str(row.get('Teléfono', '')) if pd.notna(row.get('Teléfono')) else '',
                            str(row.get('Ubicación', '')) if pd.notna(row.get('Ubicación')) else '',
                            detalles_str,
                            str(row.get('Checked', '')) if pd.notna(row.get('Checked')) else ''
                        ))
                    except Exception as e:
                        self.log(f"⚠️ Error preparando factura {row.get('Prefijo', '')}-{row.get('Número', '')}: {str(e)}")
                        continue
                
                # ✅ INSERTAR EN LOTE (MUCHO MÁS RÁPIDO)
                if datos:
                    cursor.executemany("""
                        INSERT OR REPLACE INTO facturas (
                            prefijo, numero, fecha, cliente, total,
                            subtotal_makos, impuestos_makos, propina_makos,
                            estado, tns, validacion, validacion_impuestos,
                            diferencia_impuestos, kardexid, prefijo_tns, numero_tns,
                            total_tns, neto_base_tns, iva_tns, imp_consumo_tns,
                            telefono, ubicacion, detalles, checked,
                            fecha_actualizacion
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, datos)
                
                conn.commit()
                conn.close()
                
                self.log(f"💾 SQLite guardado: {len(df)} registros")
                return True
                
        except Exception as e:
            self.log(f"❌ Error al guardar en SQLite: {str(e)}")
            import traceback
            self.log(f"🔍 Detalle del error: {traceback.format_exc()}")
            return False
    
    def factura_existe(self, prefijo, numero):
        """
        Verifica si una factura existe en SQLite
        Útil para validaciones rápidas sin cargar todo el DataFrame
        
        Args:
            prefijo: Prefijo de la factura
            numero: Número de la factura
        
        Returns:
            bool: True si existe, False en caso contrario
        """
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT 1 FROM facturas WHERE prefijo = ? AND numero = ?",
                (str(prefijo), str(numero))
            )
            
            existe = cursor.fetchone() is not None
            conn.close()
            
            return existe
            
        except Exception as e:
            self.log(f"⚠️ Error verificando factura en SQLite: {str(e)}")
            return False
    
    def exportar_a_excel(self, excel_path):
        """
        Exporta las facturas a Excel (para compatibilidad/backup)
        Mantiene el mismo formato que el Excel original
        
        Args:
            excel_path: Ruta donde guardar el Excel
        
        Returns:
            bool: True si se exportó correctamente
        """
        try:
            df = self.cargar_facturas([])  # Cargar todas
            
            if df.empty:
                self.log("⚠️ No hay datos para exportar")
                return False
            
            # Aplicar mismo formato que guardar_excel() original
            import openpyxl
            
            rename_columns = {
                'Prefijo': '🏷️ Prefijo Makos',
                'Número': '# Número Makos', 
                'Total': '💰 Total Makos',
                'SubtotalMakos': '📊 Subtotal Makos',
                'ImpuestosMakos': '🧾 Impuestos Makos',
                'PropinaMakos': '💵 Propina Makos',
                'TNS': '🔗 TNS',
                'Validacion': '✅ Validación Total',
                'ValidacionImpuestos': '📋 Validación Impuestos',
                'DiferenciaImpuestos': '⚖️ Diferencia Impuestos',
                'KARDEXID': '🔑 KARDEXID',
                'PrefijoTNS': '🏷️ Prefijo TNS',
                'NumeroTNS': '# Número TNS',
                'TotalTNS': '💰 Total TNS',
                'NetoBaseTNS': '📦 Neto Base TNS',
                'IvaTNS': '🏛️ IVA TNS',
                'ImpConsumoTNS': '🍽️ Imp. Consumo TNS',
                'Fecha': '📅 Fecha',
                'Cliente': '👤 Cliente',
                'Estado': '📈 Estado',
                'Checked': '✓ Checked',
                'Teléfono': '📞 Teléfono',
                'Ubicación': '📍 Ubicación',
                'Detalles': '📋 Detalles'
            }
            
            df_to_export = df.copy()
            columns_to_rename = {k: v for k, v in rename_columns.items() if k in df_to_export.columns}
            df_to_export.rename(columns=columns_to_rename, inplace=True)
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df_to_export.to_excel(writer, index=False, sheet_name='Facturas')
                
                worksheet = writer.sheets['Facturas']
                for idx, col in enumerate(df_to_export.columns, 1):
                    column_letter = openpyxl.utils.get_column_letter(idx)
                    max_length = max(df_to_export[col].astype(str).str.len().max(), len(str(col))) + 2
                    worksheet.column_dimensions[column_letter].width = min(max_length, 30)
            
            self.log(f"📤 Exportado a Excel: {excel_path} ({len(df_to_export)} registros)")
            return True
            
        except Exception as e:
            self.log(f"❌ Error exportando a Excel: {str(e)}")
            return False

