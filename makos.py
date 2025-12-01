import openpyxl
from urllib import response
import requests
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import pandas as pd
from datetime import datetime, timedelta
from datetime import time as dt_time  # Tipo time de datetime (para objetos time), no el módulo time
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Union
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import traceback
from pathlib import Path
import ctypes
import sys
import json
import re
import firebirdsql
import os
# ✅ IMPORTAR MÓDULO SQLite (solo para almacenamiento, NO modifica lógica)
from makos_db import MakosDatabase
# ✅ IMPORTAR GESTOR DE HORARIOS
from horarios_scraping import GestorHorariosScraping

class ScrapingManager:
    def __init__(self, app_reference=None):
        self.lock = threading.Lock()
        self.scraping_activo = False
        self.scraping_pendiente = False
        self.ultimo_tiempo_fin = None
        self.app = app_reference

    def _log(self, mensaje):
        """Método seguro para logging"""
        if self.app and hasattr(self.app, 'log'):
            self.app.log(mensaje)
        else:
            print(f"[ScrapingManager] {mensaje}")

    def scraping_manual(self, scraping_function):
        """Ejecuta scraping manual"""
        if self.scraping_activo:
            self._log("⏳ Scraping manual en cola...")
            self.scraping_pendiente = True
            return False
            
        # Ejecutar inmediatamente
        return self._ejecutar_scraping(scraping_function, "MANUAL")

    def scraping_automatico(self, scraping_function):
        """Ejecuta scraping automático"""
        if self.scraping_activo:
            self._log("⏳ Scraping automático en cola...")
            self.scraping_pendiente = True
            return False

        return self._ejecutar_scraping(scraping_function, "AUTOMÁTICO")

    def _ejecutar_scraping(self, scraping_function, tipo):
        """Función central para ejecutar scraping"""
        with self.lock:
            if self.scraping_activo:
                return False
                
            self.scraping_activo = True
            self._log(f"🚀 Iniciando scraping {tipo}...")
            
            def ejecutar():
                try:
                    resultado = scraping_function()
                    self._log(f"✅ Scraping {tipo} completado")
                    return resultado
                except Exception as e:
                    self._log(f"❌ Error en scraping {tipo}: {str(e)}")
                    return False
                finally:
                    # ✅ ESTA ES LA PARTE CRÍTICA: Siempre desactivar
                    with self.lock:
                        self.scraping_activo = False
                        self.ultimo_tiempo_fin = time.time()
                        self._log(f"🔓 Scraping {tipo} marcado como INACTIVO")
                    
                    # ✅ EJECUTAR COLA SI EXISTE
                    if self.scraping_pendiente:
                        self._log("🔄 Ejecutando scraping pendiente...")
                        self.scraping_pendiente = False
                        self.scraping_automatico(scraping_function)

            # Ejecutar en hilo separado
            threading.Thread(target=ejecutar, daemon=True).start()
            return True

    def tiempo_desde_ultimo_fin(self):
        """Retorna segundos desde el último scraping completado"""
        if self.ultimo_tiempo_fin is None:
            return float('inf')
        return time.time() - self.ultimo_tiempo_fin
    
    def get_estado_detallado(self):
        """Obtiene estado detallado para debugging"""
        return {
            'scraping_activo': self.scraping_activo,
            'scraping_pendiente': self.scraping_pendiente,
            'ultimo_tiempo_fin': self.ultimo_tiempo_fin,
            'tiempo_desde_fin': self.tiempo_desde_ultimo_fin(),
            'hilo_activo': self._scraping_thread.is_alive() if hasattr(self, '_scraping_thread') and self._scraping_thread else False
        }

    def reset_estado(self):
        """Reset completo del estado"""
        with self.lock:
            self.scraping_activo = False
            self.scraping_pendiente = False
            self.ultimo_tiempo_fin = time.time() - 1000  # Forzar ejecución
            self._log("🔄 Estado del scraping reseteado")
     
class FirebirdManager:
    """Manejador transparente de Firebird"""

    def __init__(self):
        self.conexion = None
        self.conectado = False
        self._lock = threading.Lock()  # 🔒 Para evitar condiciones de carrera
        self._insert_locks = {}
        self._facturas_procesando = set()  # ✅ NUEVO
        self._processing_lock = threading.Lock()  # ✅ NUEVO
        self._error_consecutivo_critico = False  # Flag para detener scraping por error crítico
        self._app_reference = None  # Referencia a la aplicación para detener scraping
        self._conectar()
        
        

    def _conectar(self):
        """Intenta conectar a la base de datos Firebird con reconexión automática"""
        try:
            if self.conexion:
                try:
                    self.conexion.close()
                except:
                    pass
            
            print("🔗 Intentando conectar a Firebird...")
            host = os.getenv('FIREBIRD_HOST', 'localhost')
            database = os.getenv('FIREBIRD_DB', 'C:\\DATOS TNS\\GUERREROSBURGERS2025.GDB')
            user = os.getenv('FIREBIRD_USER', 'SYSDBA')
            charset = os.getenv('FIREBIRD_CHARSET', 'ISO8859_1')

            self.conexion = firebirdsql.connect(
                host=host,
                database=database,
                user=user,
                password=os.getenv('FIREBIRD_PASSWORD', 'masterkey'),
                charset=charset
            )

            print("✅ Conexión exitosa a Firebird")
            self.conectado = True

        except Exception as e:
            print(f"❌ Error conectando a Firebird: {e}")
            self.conectado = False
            
    def _verificar_conexion(self):
        """Verifica y reconecta si la conexión se perdió"""
        try:
            if not self.conectado or not self.conexion:
                self._conectar()
                return False
            
            # Intentar una consulta simple para verificar
            cur = self.conexion.cursor()
            cur.execute("SELECT 1 FROM RDB$DATABASE")
            cur.fetchone()
            cur.close()
            return True
        except:
            print("🔁 Conexión perdida, reconectando...")
            self.conectado = False
            self._conectar()
            return self.conectado

    def factura_existe(self, prefijo, numero):
        """Verifica si la factura ya existe en TNS con manejo de reconexión"""
        with self._lock:
            if not self._verificar_conexion():
                return False, None, 0.0, 0.0, 0.0, 0.0, '', ''

            cur = None
            try:
                cur = self.conexion.cursor()
                observ_value = f"{prefijo}{numero}"
                query = """
                    SELECT KARDEXID, TOTAL, NETOBASE, NETOIVA, VRICONSUMO, CODPREFIJO, NUMERO FROM KARDEX 
                    WHERE  OBSERV = ?
                """
                cur.execute(query, (observ_value,))
                resultado = cur.fetchone()

                if resultado:
                    kardexid, total_tns, netobase, netoiva, vriconsumo, codprefijo_tns, numero_tns = resultado
                    self._log_safe(f"🔍 Factura encontrada en TNS: OBSERV={observ_value}, KARDEXID={kardexid}, TOTAL={total_tns}")
                    return (True, kardexid, float(total_tns) if total_tns else 0.0, 
                            float(netobase) if netobase else 0.0, float(netoiva) if netoiva else 0.0, 
                            float(vriconsumo) if vriconsumo else 0.0, 
                            codprefijo_tns, numero_tns)  # ✅ AGREGAR PREFIJO Y NUMERO TNS
                else:
                    self._log_safe(f"🔍 Factura NO encontrada en TNS: {observ_value}")
                    return False, None, 0.0, 0.0, 0.0, 0.0, '', ''

            except Exception as e:
                self._log_safe(f"❌ Error verificando factura en TNS: {str(e)}")
                self.conectado = False
                return False, None, 0.0, 0.0, 0.0, 0.0, '', ''
            finally:
                if cur:
                    cur.close()  

    def _log_safe(self, mensaje):
        """Método seguro para logging desde hilos"""
        try:
            if hasattr(self, 'root'):
                self.root.after(0, lambda: self.log(mensaje))
            else:
                print(mensaje)  # Fallback si no hay GUI
        except:
            print(f"[FALLBACK LOG] {mensaje}")

    def insertar_factura(self, factura):
        # ✅ EXTRAER PREFIJO Y NÚMERO
        try:
            if isinstance(factura, str):
                factura_dict = json.loads(factura)
                prefijo = factura_dict['Prefijo']
                numero = str(factura_dict['Número'])
            else:
                prefijo = factura['Prefijo']
                numero = str(factura['Número'])
        except Exception as e:
            self._log_safe(f"❌ Error extrayendo datos de factura: {str(e)}")
            return False
    
        factura_id = f"{prefijo}-{numero}"
        
        # ✅ 1. VERIFICACIÓN EN MEMORIA (NUEVO - FALTABA)
        with self._processing_lock:
            if factura_id in self._facturas_procesando:
                self._log_safe(f"🚫 YA EN PROCESO: {factura_id}")
                return False
            self._facturas_procesando.add(factura_id)
            
        try:
            # ✅ 2. VERIFICAR CONEXIÓN
            if not self._verificar_conexion():
                self._log_safe("⚠️ No hay conexión a Firebird")
                return False
    
            # ✅ 3. VERIFICAR SI EXISTE EN TNS
            self._log_safe(f"🔍 VALIDACIÓN ANTIDUPLICADOS: {prefijo}-{numero}")
            existe_en_tns, kardexid, total_tns, netobase_tns, netoiva_tns, vriconsumo_tns, prefijo_tns, numero_tns = self.factura_existe(prefijo, numero)
    
            if existe_en_tns:
                self._log_safe(f"🚫 BLOQUEADO: {prefijo}-{numero} YA EXISTE en TNS")
                return False
    
            # ✅ 4. LOCK ESPECÍFICO POR FACTURA
            lock_key = f"{prefijo}_{numero}"
            with self._lock:
                if lock_key not in self._insert_locks:
                    self._insert_locks[lock_key] = threading.Lock()
                factura_lock = self._insert_locks[lock_key]
    
            with factura_lock:
                # ✅ 5. VERIFICACIÓN FINAL (POR SI ACASO CAMBIÓ ALGO)
                existe_en_tns = self.factura_existe(prefijo, numero)[0]
                if existe_en_tns:
                    self._log_safe(f"🚫 DUPLICADO DETECTADO EN ÚLTIMO MOMENTO: {factura_id}")
                    return False
    
                cur = None
                try:
                    # Convertir factura si es necesario
                    if isinstance(factura, str):
                        factura = json.loads(factura)
    
                    try:
                        # Si es Timestamp de pandas, convertirlo a string primero
                        if hasattr(factura['Fecha'], 'strftime'):
                            fecha_str = factura['Fecha'].strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            fecha_str = str(factura['Fecha'])
    
                        fecha = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S').date()
    
                    except Exception as e:
                        self._log_safe(f"❌ Error procesando fecha {factura['Fecha']}: {str(e)}")
                        # Usar fecha actual como fallback
                        fecha = datetime.now().date()
                        self._log_safe(f"⚠️ Usando fecha actual como fallback: {fecha}")
    
    
                    if not self._verificar_conexion():
                        raise Exception("Conexión perdida al actualizar totales")
    
                    prefijo = factura['Prefijo']
    
    
                    # 🔄 Asegurarse de que 'Detalles' sea dict
                    if isinstance(factura['Detalles'], str):
                        detalles = json.loads(factura['Detalles'])
                        # ✅ Actualiza en el objeto original
                        factura['Detalles'] = detalles
                    else:
                        detalles = factura['Detalles']
    
    
    
                    # ✅ PROCESAR NIT UNA SOLA VEZ (disponible para toda la función)
                    nit_obtenido = detalles.get('nit', '222222222222')
                    nit_str = str(nit_obtenido).strip() if nit_obtenido else '222222222222'
                    
                    # ✅ LOGGING DETALLADO PARA DEBUG
                    self._log_safe(f"🔍 [DEBUG NIT] Valor obtenido: {repr(nit_obtenido)}")
                    self._log_safe(f"🔍 [DEBUG NIT] Tipo: {type(nit_obtenido).__name__}")
                    self._log_safe(f"🔍 [DEBUG NIT] Como string: {repr(nit_str)}")
                    self._log_safe(f"🔍 [DEBUG NIT] Condición: {nit_str != '222222222222'}")
                    
                    if nit_str != '222222222222':
                        if not self._verificar_conexion():
                            raise Exception("Conexión perdida al verificar tercero")
                        cur = self.conexion.cursor()
                        
                        # ✅ LOGGING ANTES DE CONSULTA
                        self._log_safe(f"🔍 [DEBUG NIT] Consultando Firebird con NIT: {repr(nit_str)}")
                        cur.execute("SELECT TERID,EMAIL FROM TERCEROS WHERE NIT = ?", (nit_str,))
                        resultado_tercero_id = cur.fetchone()
                        
                        # ✅ LOGGING DESPUÉS DE CONSULTA
                        if resultado_tercero_id:
                            self._log_safe(f"🔍 [DEBUG NIT] Tercero encontrado: {resultado_tercero_id}")
                        else:
                            self._log_safe(f"🔍 [DEBUG NIT] Tercero NO encontrado en Firebird")
    
                        if resultado_tercero_id:
                            ter_id, ter_email = resultado_tercero_id
                            self._log_safe(f"🔍 ID del tercero encontrado: {ter_id}")
                            self._log_safe(f"🔍 Email actual del tercero: {ter_email}")
                            # Pequeña pausa para evitar problemas de concurrencia
                            time.sleep(5)
    
                            # OBTENER EMAIL DEL JSON (si existe y no está vacío)
                            email_json = detalles.get('email', '').strip()
                            email_env = os.getenv('EMAIL', '').strip()
    
                            # LÓGICA ACTUALIZADA:
                            email_a_usar = None
    
                            if email_json:  # 1. PRIORIDAD: SIEMPRE usar email del JSON si existe
                                email_a_usar = email_json
                                self._log_safe(f"✉️ Actualizando con email del JSON: {email_json}")
                            elif not ter_email or ter_email.strip() == '':  # 2. Solo usar ENV si el tercero no tenía email
                                if email_env:
                                    email_a_usar = email_env
                                    self._log_safe(f"✉️ Actualizando con email del environment: {email_env}")
                                else:
                                    self._log_safe("ℹ️ No hay email para actualizar")
                            else:
                                self._log_safe("ℹ️ Manteniendo email actual del tercero")
    
                            # Actualizar solo si hay un email definido para usar
                            if email_a_usar is not None:
                                cur.execute("UPDATE TERCEROS SET EMAIL = ? WHERE TERID = ?", (email_a_usar, ter_id))
                                self._log_safe(f"✅ Email actualizado para el tercero {ter_id}: {email_a_usar}")
    
                        else:
                            self._log_safe(f"❌ No se pudo obtener el ID del tercero")
                            # Crear nuevo tercero - PRIORIDAD: email del JSON primero
                            email_json = detalles.get('email', '').strip()
                            email_env = os.getenv('EMAIL', '').strip()
    
                            email_a_usar = email_json if email_json else email_env
                            
                            # ✅ CONSULTAR ENDPOINT /Contacts/{idcontact} PARA OBTENER postalcode
                            tipo_documento = 'N'  # Valor por defecto (segundo parámetro)
                            idcontact = detalles.get('idcontact', 0)
                            
                            if idcontact and idcontact != 0:
                                try:
                                    self._log_safe(f"🔍 Consultando contacto {idcontact} para obtener postalcode...")
                                    contact_url = f"https://pos.appmakos.com:3333/Contacts/{idcontact}"
                                    
                                    if not hasattr(self, 'HEADERS') or not self.HEADERS:
                                        self._log_safe("⚠️ HEADERS no disponible, usando tipo de documento por defecto 'N'")
                                    else:
                                        contact_response = requests.get(
                                            contact_url, 
                                            headers=self.HEADERS, 
                                            timeout=10
                                        )
                                        
                                        if contact_response.status_code == 200:
                                            contact_data = contact_response.json()
                                            postalcode = contact_data.get('postalcode', '').strip()
                                            
                                            self._log_safe(f"📋 Contacto obtenido - postalcode: {repr(postalcode)}")
                                            
                                            if postalcode == 'J':
                                                tipo_documento = 'J'
                                                self._log_safe(f"✅ postalcode es 'J', usando tipo de documento 'J' (segundo parámetro)")
                                            else:
                                                self._log_safe(f"ℹ️ postalcode no es 'J' ({repr(postalcode)}), usando tipo de documento por defecto 'N'")
                                        else:
                                            self._log_safe(f"⚠️ Error al consultar contacto (HTTP {contact_response.status_code}), usando tipo de documento por defecto 'N'")
                                except Exception as e:
                                    self._log_safe(f"⚠️ Error consultando contacto: {str(e)}, usando tipo de documento por defecto 'N'")
                            else:
                                self._log_safe(f"ℹ️ idcontact no disponible o es 0, usando tipo de documento por defecto 'N'")
    
                            self._log_safe(f"➕ Creando nuevo tercero con NIT: {nit_str}, Tipo de documento: {tipo_documento}")
                            params = (
                                nit_str,  # NIT - primer parámetro
                                tipo_documento,   # Tipo de documento - SEGUNDO PARÁMETRO (J o N según postalcode)
                                nit_str,  # Documento - tercer parámetro
                                detalles.get('alias', 'Consumidor Final'),  # Nombre - cuarto parámetro
                                None,            # Dirección (NULL) - quinto parámetro
                                'N',             # Estado - sexto parámetro (siempre 'N')
                                email_a_usar     # Email - séptimo parámetro
                            )
    
                            if email_a_usar:
                                self._log_safe(f"✉️ Email para nuevo tercero: {email_a_usar}")
                            else:
                                self._log_safe("⚠️ No se definió email para el nuevo tercero")
    
                            # Modificar la llamada al procedimiento para incluir el email
                            cur.execute("SELECT * FROM TNS_INS_TERCERO(?,?,?,?,?,?,?)", params)
                            resultado_tercero = cur.fetchone()
                            if not resultado_tercero:
                                self._log_safe(f"❌ Tercero no encontrado o error en inserción")
                            else:
                                self._log_safe(f"✅ Tercero insertado correctamente")
    
                    # 💰 Procesar propina si existe
                    if detalles.get('tip', 0) > 0:
                        self._log_safe(f"💰 Propina detectada: {detalles['tip']}")
    
                        detalles['items'].append({
                            "iditem": 3,
                            "codebar": "TIP",
                            "name": "PROPINAS",
                            "quantity": 1,
                            "subtotal": detalles['tip'],
                            "idtax": 0,
                            "taxname": "",
                            "idfiscal": "",
                            "fiscalname": "",
                            "fee": 0,
                            "taxes": 0,
                            "discount": 0,
                            "devolution": 0,
                            "idorder": 0,
                            "vunitario": detalles['tip'],
                            "vunitariotax": 0.0,
                            "vunitariototal": detalles['tip'],
                            "vtotal": detalles['tip']
                        })
                    else:
                        self._log_safe("💰 No se detectó propina en la factura")
                    print(f"DEBUG - Detalles de la factura: {detalles}")
                    payments = detalles['payments']
                    prefijo = factura['Prefijo']
                    discount = float(0.00)
    
                    # ✅ REEMPLAZAR VARIABLE ENV POR CHECKBOX DE LA INTERFAZ
                    # Obtener el valor del checkbox reverse de la aplicación principal
                    reverse_mode = self.reverse_var.get() if hasattr(self, 'reverse_var') else False
    
                    for payment in payments:
                        is_cash_to_final_consumer = (
                            len(payments) == 1 and 
                            payment['payname'] == 'Efectivo' and 
                            detalles['nit'] == '222222222222'
                        )
                        is_low_value = payment['valuepay'] < 1

                        if ((reverse_mode and (is_cash_to_final_consumer or is_low_value)) or os.getenv('ALWAYS_REVERSE', 'false').lower() == 'true'):
                            original_prefijo = prefijo
                            prefijo = prefijo[::-1]
                            self._log_safe(f"🔁 Prefijo invertido: {original_prefijo} → {prefijo}")
    
    
                    if not self._verificar_conexion():
                        raise Exception("Conexión perdida al obtener consecutivo")
    
                    cur = self.conexion.cursor()
                    numero = 1
                    cur.execute("SELECT CONSECUTIVO FROM CONSECUTIVO WHERE CODCOMP = ? AND CODPREFIJO = ?", ('FV', prefijo))
                    resultado = cur.fetchone()
    
                    if not resultado:
                        self._log_safe(f"❌ Prefijo {prefijo} no encontrado en CONSECUTIVO")
                    else:
                        numero = int(resultado[0])+1
    
                    numero = str(numero)
                    self._log_safe(f"\n=== PROCESANDO FACTURA {prefijo}-{numero} ===")
    
                    cur = self.conexion.cursor()
    
                    # 1. Insertar cabecera con sistema de reintentos
                    self._log_safe("📝 Insertando cabecera...")
    
                    if not self._verificar_conexion():
                        raise Exception("Conexión perdida al insertar cabecera")
    
                    # ✅ USAR nit_str QUE YA FUE PROCESADO ARRIBA (con strip y validación)
                    nit_real = nit_str
                    self._log_safe(f"🔍 [DEBUG NIT] NIT para inserción cabecera: {repr(nit_real)}")
                    
                    # ✅ SISTEMA DE REINTENTOS CON VERIFICACIÓN DE CONSECUTIVO
                    max_intentos = 3
                    intento = 0
                    cabecera_insertada = False
                    numero_final = numero
                    
                    while intento < max_intentos and not cabecera_insertada:
                        intento += 1
                        self._log_safe(f"🔄 Intento {intento}/{max_intentos} de inserción de cabecera con consecutivo: {numero_final}")
                        
                        cabecera_query = "SELECT * FROM TNS_INS_FACTURAVTA(?,?,?,?,?,?,?,?,?,?,?,?,?)"
                        cabecera_params = (factura['Prefijo'] + factura['Número'], 'FV', prefijo, numero_final, fecha, fecha.strftime("%m"), 'MU', '0', 'ADMIN', prefijo, nit_real, None, '2')
                        
                        self._log_safe(f"DEBUG - Query cabecera: {cabecera_query}")
                        self._log_safe(f"DEBUG - Params cabecera: {cabecera_params}")
                        
                        try:
                            cur.execute(cabecera_query, cabecera_params)
                            resultado_cabecera = cur.fetchone()
                            self.conexion.commit()
                            self._log_safe(f"DEBUG - Resultado cabecera: {resultado_cabecera}")
                            
                            # Verificar si la inserción fue exitosa
                            if resultado_cabecera and resultado_cabecera[0] != 0:
                                # Verificar si realmente se insertó en KARDEX
                                cur.execute("SELECT KARDEXID FROM KARDEX WHERE CODPREFIJO = ? AND NUMERO = ? AND CODCOMP = ?", (prefijo, numero_final, 'FV'))
                                kardex_existe = cur.fetchone()
                                
                                if kardex_existe:
                                    self._log_safe(f"✅ Cabecera insertada exitosamente con consecutivo: {numero_final}")
                                    numero = numero_final
                                    cabecera_insertada = True
                                else:
                                    self._log_safe(f"⚠️ Procedimiento devolvió éxito pero no se encontró en KARDEX. Reintentando...")
                                    self.conexion.rollback()
                            else:
                                # El procedimiento devolvió error, verificar si el consecutivo ya existe
                                self._log_safe(f"⚠️ Procedimiento devolvió error. Verificando si consecutivo {numero_final} ya existe...")
                                cur.execute("SELECT KARDEXID FROM KARDEX WHERE CODPREFIJO = ? AND NUMERO = ? AND CODCOMP = ?", (prefijo, numero_final, 'FV'))
                                kardex_existe = cur.fetchone()
                                
                                if kardex_existe:
                                    self._log_safe(f"🔍 Consecutivo {numero_final} ya existe en KARDEX. Obteniendo siguiente consecutivo...")
                                    # Obtener el siguiente consecutivo disponible
                                    cur.execute("SELECT MAX(CAST(NUMERO AS INTEGER)) FROM KARDEX WHERE CODCOMP = ? AND CODPREFIJO = ?", ('FV', prefijo))
                                    max_num = cur.fetchone()[0]
                                    if max_num:
                                        numero_final = str(int(max_num) + 1)
                                        self._log_safe(f"📈 Nuevo consecutivo obtenido: {numero_final}")
                                    else:
                                        # Si no hay facturas, usar el consecutivo de la tabla
                                        cur.execute("SELECT CONSECUTIVO FROM CONSECUTIVO WHERE CODCOMP = ? AND CODPREFIJO = ?", ('FV', prefijo))
                                        resultado = cur.fetchone()
                                        if resultado:
                                            numero_final = str(int(resultado[0]) + 1)
                                            self._log_safe(f"📈 Consecutivo desde tabla: {numero_final}")
                                else:
                                    # No existe, pero falló la inserción. Reintentar con mismo número
                                    self._log_safe(f"⚠️ Consecutivo {numero_final} no existe pero falló inserción. Reintentando...")
                                
                                self.conexion.rollback()
                                
                        except Exception as e:
                            error_msg = str(e)
                            self._log_safe(f"❌ Error en intento {intento}: {error_msg}")
                            
                            # Verificar si el error es porque el consecutivo ya existe
                            if "asentado" in error_msg.lower() or "ya existe" in error_msg.lower() or "duplicado" in error_msg.lower() or "no se puede modificar" in error_msg.lower():
                                self._log_safe(f"🔍 Error sugiere que consecutivo {numero_final} ya existe. Verificando...")
                                cur.execute("SELECT KARDEXID FROM KARDEX WHERE CODPREFIJO = ? AND NUMERO = ? AND CODCOMP = ?", (prefijo, numero_final, 'FV'))
                                kardex_existe = cur.fetchone()
                                
                                if kardex_existe:
                                    self._log_safe(f"✅ Confirmado: consecutivo {numero_final} ya existe. Obteniendo siguiente...")
                                    # Obtener el siguiente consecutivo disponible
                                    cur.execute("SELECT MAX(CAST(NUMERO AS INTEGER)) FROM KARDEX WHERE CODCOMP = ? AND CODPREFIJO = ?", ('FV', prefijo))
                                    max_num = cur.fetchone()[0]
                                    if max_num:
                                        numero_final = str(int(max_num) + 1)
                                        self._log_safe(f"📈 Nuevo consecutivo obtenido: {numero_final}")
                                    else:
                                        cur.execute("SELECT CONSECUTIVO FROM CONSECUTIVO WHERE CODCOMP = ? AND CODPREFIJO = ?", ('FV', prefijo))
                                        resultado = cur.fetchone()
                                        if resultado:
                                            numero_final = str(int(resultado[0]) + 1)
                                            self._log_safe(f"📈 Consecutivo desde tabla: {numero_final}")
                            
                            self.conexion.rollback()
                            
                            if intento >= max_intentos:
                                # Error crítico: detener scraping
                                self._log_safe(f"🚨 ERROR CRÍTICO: No se pudo insertar cabecera después de {max_intentos} intentos")
                                self._log_safe(f"🚨 Factura: {prefijo}-{factura['Número']}, Último consecutivo intentado: {numero_final}")
                                self._log_safe(f"🚨 PROBLEMA EN CONSECUTIVO: El sistema no puede continuar. Scraping DETENIDO.")
                                self._error_consecutivo_critico = True
                                
                                # Detener scraping si hay referencia a la aplicación
                                if self._app_reference:
                                    try:
                                        self._app_reference.scraping_manager.scraping_activo = False
                                        self._app_reference.log(f"🛑 SCRAPING DETENIDO por error crítico en consecutivo")
                                    except:
                                        pass
                                
                                raise Exception(f"Error crítico en consecutivo después de {max_intentos} intentos. Scraping detenido.")
                    
                    if not cabecera_insertada:
                        raise Exception(f"No se pudo insertar cabecera después de {max_intentos} intentos")
                    
                    # Actualizar numero con el número final usado
                    numero = numero_final
    
                    # 2. Procesar artículos
                    detalles = factura['Detalles']['items'] if isinstance(factura['Detalles'], dict) else json.loads(factura['Detalles'])['items']
                    self._log_safe(f"🛒 Procesando {len(detalles)} artículos...")
    
                    for detalle in detalles:
                    
                        if not self._verificar_conexion():
                            raise Exception("Conexión perdida durante procesamiento de artículos")
                        codebar = detalle.get('codebar', '')
                        nombre = detalle.get('name', 'Artículo sin descripción')
                        #precio = float(detalle.get('vunitariototal', 0))-(float(detalle.get('discount', 0))/(int(detalle.get('quantity', 1))))
                        cantidad = int(detalle.get('quantity', 1))
                        if cantidad == 0:
                            cantidad = 1  # Evitar división por cero
                        precio = float(detalle.get('vunitariototal', 0)) - (float(detalle.get('discount', 0)) / cantidad)
    
                        porcentaje = float(detalle.get('fee', 0))
                        taxname = detalle.get('fiscalname', '')
                        # sumar a discountglobal
                        discount += precio
    
                        self._log_safe(f"\n🔍 Artículo: {codebar} - {nombre}")
    
                        # Verificar existencia
                        cur.execute("SELECT COUNT(*) FROM MATERIAL WHERE CODIGO = ?", (codebar,))
                        if cur.fetchone()[0] == 0:
                            self._log_safe(f"➕ Creando artículo: {codebar}")
                            material_query = "SELECT * FROM TNS_INS_MATERIAL(?,?,?,?,?,?,?)"
                            material_params = (codebar, nombre, '00.01.99', '00', '01', '0', precio)
    
                            self._log_safe(f"DEBUG - Query material: {material_query}")
                            self._log_safe(f"DEBUG - Params material: {material_params}")
    
                            cur.execute(material_query, material_params)
                            resultado_material = cur.fetchone()
                            self._log_safe(f"DEBUG - Resultado material: {resultado_material}")
    
                            if not resultado_material or resultado_material[0] == 0:
                                raise Exception(f"Error al crear artículo {codebar}")
                            else:
                                response = cur.execute("SELECT MATID FROM MATERIAL WHERE CODIGO = ?", (codebar,))
                                material_id = response.fetchone()[0]
                                #if taxname == 'INC':
                                #    self._log_safe(f"🔄 Actualizando impuesto para artículo {codebar} a 'INC'")
                                #    cur.execute("UPDATE MATERIALSUC SET PORcd..CONS = ?, IMPCONS = ? WHERE MATID = ?", (porcentaje, 0, material_id))
    
                        # Insertar detalle
                        detalle_query = "SELECT * FROM TNS_INS_DETALLEFACTVTA(?,?,?,?,?,?,?)"
                        detalle_params = (numero, codebar, '0', str(cantidad), precio, prefijo, 'FV')
    
                        self._log_safe(f"DEBUG - Query detalle: {detalle_query}")
                        self._log_safe(f"DEBUG - Params detalle: {detalle_params}")
    
                        cur.execute(detalle_query, detalle_params)  # 20475119
                        resultado_detalle = cur.fetchone()
                        self._log_safe(f"DEBUG - Resultado detalle: {resultado_detalle}")
    
                        if not resultado_detalle or resultado_detalle[0] == 0:
                            raise Exception(f"Error al insertar detalle para artículo {codebar}")
    
                    # 901596913-5
                    # 2.1 PROCESAR FORMA DE PAGO ya cargue la []0 no nesecito recorrerla
                    # Antes de llamar a TNS_INS_DEKARDEXFP, verificar que existe el kardex
                    cur.execute("SELECT 1 FROM KARDEX WHERE NUMERO = ? AND CODCOMP = ? AND CODPREFIJO = ?", (numero, 'FV', prefijo))
                    if not cur.fetchone():
                        # Si no existe, esperar un momento y reintentar
                        time.sleep(0.5)
                        self._log_safe(f"🔄 Reintentando verificación de kardex... con parametros: {{'Número': {numero}, 'CodComp': 'FV', 'CodPrefijo': {prefijo}}}")
                        cur.execute("SELECT 1 FROM KARDEX WHERE NUMERO = ? AND CODCOMP = ? AND CODPREFIJO = ?", (numero, 'FV', prefijo))
                        if not cur.fetchone():
                            self._log_safe("❌ No se encontró el kardex para la factura")
                            return False
    
                    self._log_safe("💳 Procesando forma de pago...")
    
                    pagos = factura['Detalles'] if isinstance(factura['Detalles'], dict) else json.loads(factura['Detalles'])
                    cantidaddepagos = len(pagos['payments'])
                    totalfp = float(pagos.get('totalfp', 0))
                    if not self._verificar_conexion():
                        raise Exception("Conexión perdida durante procesamiento de pagos")
                    for payments in pagos['payments']:
                        self._log_safe(f"DEBUG - Pagos: {payments}")
                        self._log_safe(f"DEBUG - Query detalle: {detalle_query}")
                        paycode = str(payments['paycode'])
                        valuepay = float(payments['valuepay'])
                        totalfp += valuepay
    
                        params = (
                            str(numero),                      # VNUMERO
                            'FV',                             # VCODCOMP
                            str(prefijo),                     # VCODPREFIJO
                            paycode,         # VFPCODIGO
                            '901596913-5',                    # VNITTRI
                            valuepay       # VTOTAL
                        )
    
                        self._log_safe(f"DEBUG - Params pago: {params}")
    
                        response = cur.execute("SELECT * FROM TNS_INS_DEKARDEXFP (?,?,?,?,?,?)", params)
    
                        resultado_pago = cur.fetchone()
                        self._log_safe(f"DEBUG - Resultado pago: {resultado_pago}")
    
                        if not resultado_pago or resultado_pago[0] == 0:
                            raise Exception(f"Error al insertar pago para método {payments['paycode']}")
    
                        self._log_safe("✅ Forma de pago procesada correctamente")
    
                    # 3. Actualizar totales
                    self._log_safe("🧮 Actualizando totales...")
    
                    if not self._verificar_conexion():
                        raise Exception("Conexión perdida al actualizar totales")
    
                    totales_query = "SELECT * FROM TNS_ACTTOTALFACT(?, ?, ?)"
                    totales_params = ('FV', prefijo, numero)
    
                    self._log_safe(f"DEBUG - Query totales: {totales_query}")
                    self._log_safe(f"DEBUG - Params totales: {totales_params}")
    
                    cur.execute(totales_query, totales_params)
                    resultado_totales = cur.fetchone()
                    self._log_safe(f"DEBUG - Resultado totales: {resultado_totales}")
    
                    # Confirmar transacción
                    self.conexion.commit()
                    self._log_safe(f"✅ FACTURA {prefijo}-{numero} COMPLETADA Y CONFIRMADA")
                    # detalles['tns']= prefijo + numero
                    
                    fecha_sql = fecha.strftime('%Y-%m-%d')
    
                    if not self._verificar_conexion():
                        raise Exception("Conexión perdida durante actualizaciones finales")
    
                    cur.execute("SELECT CENID FROM CENTROS WHERE NRO= ?", (factura['Prefijo'],))
                    resultado = cur.fetchone()
                    vcentro = resultado[0] if resultado else '1'
                    vcodcomp = 'FV'  # Código de la compañía
                    vcodprefijo = prefijo  # Prefijo de la factura
                    vnumero = numero
    
                    cur.execute("""
                                    UPDATE KARDEX
                                    SET FECASENTAD = ?, CENID = ?
                                    WHERE CODCOMP = ? AND CODPREFIJO = ? AND NUMERO = ?
                                """, (
                        fecha_sql,
                        vcentro,
                        vcodcomp,
                        vcodprefijo,
                        vnumero
                    ))
    
                    time.sleep(0.2)  # Delay importante para Firebird
    
                    # SEGUNDO UPDATE (HORA y OBSERV)
                    hora_24 = datetime.now().strftime('%H:%M')
                    self._log_safe(f"🕒 Actualizando hora: {hora_24}")
                    cur.execute("""
                        UPDATE KARDEX
                        SET HORAASEN = ?, HORA = ?, OBSERV = ?
                        WHERE CODCOMP = ? AND CODPREFIJO = ? AND NUMERO = ?
                    """, (
                        hora_24,
                        hora_24,
                        factura['Prefijo'] + factura['Número'],
                        vcodcomp,
                        vcodprefijo,
                        vnumero
                    ))
    
                    # --- VERIFICACIÓN ADICIONAL PARA LA ÚLTIMA FACTURA ---
                    cur.execute("""
                        SELECT FECASENTAD, HORAASEN FROM KARDEX
                        WHERE CODCOMP = ? AND CODPREFIJO = ? AND NUMERO = ?
                    """, (vcodcomp, vcodprefijo, vnumero))
    
                    resultado = cur.fetchone()
                    if not resultado or resultado[0] is None or resultado[1] is None:
                        self._log_safe("⚠️ Campos NULL detectados - Reintentando UPDATE...")
                        cur.execute("""
                            UPDATE KARDEX
                            SET FECASENTAD = ?, HORAASEN = ?
                            WHERE CODCOMP = ? AND CODPREFIJO = ? AND NUMERO = ?
                        """, (
                            fecha_sql,
                            hora_24,
                            vcodcomp,
                            vcodprefijo,
                            vnumero
                        ))
    
                    # --- BLOQUE DE ACTUALIZACIÓN DE CONSECUTIVO (CRÍTICO) ---
                    cur.execute("""
                        SELECT MAX(CAST(NUMERO AS INTEGER))
                        FROM KARDEX
                        WHERE CODCOMP = 'FV' AND CODPREFIJO = ?
                    """, (prefijo,))
                    max_num = cur.fetchone()[0]
    
                    self._log_safe(f"🔢 Actualizando consecutivo: {max_num} para prefijo {prefijo}")
                    cur.execute("""
                        UPDATE CONSECUTIVO
                        SET CONSECUTIVO = ?
                        WHERE SUCID = 1 AND CODCOMP = 'FV' AND CODPREFIJO = ?
                    """, (str(max_num), prefijo))
    
                    self.conexion.commit()
                    self._log_safe(f"✅ Factura {prefijo}-{vnumero} completada")
                    return True
    
                except Exception as e:
                    self._log_safe(f"❌ ERROR en inserción: {str(e)}")
                    # Marcar conexión como defectuosa
                    self.conectado = False
                    if self.conexion:
                        try:
                            self.conexion.rollback()
                        except:
                            pass
                    return False
                finally:
                    if cur:
                        cur.close()
          
        finally:
            # ✅ 7. SIEMPRE LIBERAR DE MEMORIA
            with self._processing_lock:
                if factura_id in self._facturas_procesando:
                    self._facturas_procesando.remove(factura_id)

    def __del__(self):
        """Cierra conexión al destruirse"""
        if self.conexion:
            self.conexion.close()

def ocultar_consola():
    """Oculta la ventana de la consola en Windows"""
    if sys.platform == 'win32':
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)

# Ocultar consola solo si no está en modo de depuración
if not hasattr(sys, 'gettrace') or sys.gettrace() is None:
    ocultar_consola()

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        if getattr(sys, 'frozen', False):  # Si está empaquetado como .exe
            # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(sys.executable))
        else:  # Si se ejecuta desde el código fuente
            base_path = os.path.dirname(os.path.abspath(__file__))
    except:
        base_path = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    
    full_path = os.path.join(base_path, relative_path)
    return full_path

# Ruta base del proyecto - CORREGIDO para .exe
if getattr(sys, 'frozen', False):
    # Si está compilado como .exe, usar el directorio donde está el .exe
    BASE_DIR = Path(sys.executable).parent
else:
    # Si se ejecuta como script, usar el directorio del script
    BASE_DIR = Path(__file__).parent

class AplicacionScraping:
    def __init__(self, root):
        self.root = root
        self.driver = None
        self.factura_actual = None
        self.df_lock = threading.Lock()
        self.DIAS_HISTORICO = int(os.getenv('DIAS_HISTORICO', 2))
        self.EXCEL_FILE = os.path.join(BASE_DIR, os.getenv('EXCEL_FILE', 'Facturas_Guerreros.xlsx'))
        self.facturas_procesando = set()  # ✅ NUEVO
        self.processing_lock = threading.Lock()  # ✅ NUEVO
        self.scraping_manager = ScrapingManager(app_reference=self)
        
        # ✅ INICIALIZAR GESTOR DE HORARIOS
        self.gestor_horarios = GestorHorariosScraping()
        
        # ✅ RASTREAR ESTADO ANTERIOR DEL HORARIO para detectar cambios
        self.horario_anterior_activo = None  # None = primera vez, True/False = estado anterior
        
        # ✅ RASTREAR ÚLTIMA RENOVACIÓN DE SESIÓN (para renovación periódica)
        self.ultima_renovacion_sesion = None  # Timestamp de última renovación
        self.INTERVALO_RENOVACION_SESION = 3600  # Renovar sesión cada 1 hora (3600 segundos)

        # ✅ INICIALIZAR ARCHIVO DE LOG
        self.log_file = None
        self._inicializar_log_file()

        # ✅ INICIALIZAR VARIABLES DE CHECKBOXES PRIMERO
        self.usar_fechas_var = tk.BooleanVar(value=False)  # Ya no se usa, pero se mantiene por compatibilidad
        self.dia_actual_var = tk.BooleanVar(value=True)  # Por defecto usar día actual
        self.intervalo_var = tk.StringVar(value="30")  # Valor por defecto (se actualizará según horario)

        self.inicializar_variables()
        
        # ✅ INICIALIZAR SQLite (se inicializará después de que self.log esté disponible)
        self.db = None  # Se inicializará después

        # 1. Verificar archivos requeridos
        self.verificar_archivos_iniciales()

        # 2. Cargar configuración
        self.cargar_configuracion()

        # 3. Inicializar interfaz
        self.inicializar_interfaz()

        # 4. Configurar estilos de log
        self.log_textbox.tag_config("success", foreground="green")
        self.log_textbox.tag_config("error", foreground="red")
        self.log_textbox.tag_config("warning", foreground="orange")
        self.log_textbox.tag_config("info", foreground="black")
        
        # ✅ INICIALIZAR SQLite AHORA (después de que self.log esté disponible)
        if self.db is None:
            self.db = MakosDatabase(log_callback=self.log)
            
            # ✅ MIGRAR Excel a SQLite si existe (solo una vez)
            if hasattr(self, '_excel_existe') and self._excel_existe and os.path.exists(self.EXCEL_FILE):
                try:
                    self.log("🔄 Detectado Excel existente - Migrando a SQLite...")
                    df_excel = pd.read_excel(
                        self.EXCEL_FILE,
                        engine='openpyxl',
                        dtype={'Número': str, 'Prefijo': str}
                    )
                    if self.db.guardar_facturas(df_excel):
                        self.log(f"✅ Migración completada: {len(df_excel)} facturas migradas a SQLite")
                        # Opcional: Backup de Excel
                        backup_excel = self.EXCEL_FILE.replace('.xlsx', '_backup_migrado.xlsx')
                        try:
                            import shutil
                            shutil.copy2(self.EXCEL_FILE, backup_excel)
                            self.log(f"📦 Backup de Excel guardado: {backup_excel}")
                        except:
                            pass
                except Exception as e:
                    self.log(f"⚠️ Error al migrar Excel: {str(e)}")

        # 5. Carga inicial de datos
        self.cargar_facturas()
        
        # 6. Verificar si hay preferencia guardada
        preferencia = self.cargar_preferencia_inicio()
        if preferencia:
            # Usar preferencia guardada
            if preferencia == "automatico":
                self.auto_scraping_var.set(True)
                self.log("🔄 Modo AUTOMÁTICO (preferencia guardada)")
                self.programar_scraping_automatico()
            elif preferencia == "manual":
                self.auto_scraping_var.set(False)
                self.log("✋ Modo MANUAL (preferencia guardada)")
            elif preferencia == "solo_ver":
                self.auto_scraping_var.set(False)
                self.log("👁️ Modo SOLO VER (preferencia guardada)")
        else:
            # Mostrar diálogo de inicio
            self.mostrar_dialogo_inicio()

        # 7. Configurar cierre seguro
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.conexion_firebird = None
        self.firebird = FirebirdManager()
        self.firebird._app_reference = self  # Pasar referencia para poder detener scraping
        self._login_semaphore = threading.Semaphore(1)

        # Log inicial
        self.log(f"\n{'='*50}")
        self.log(f"✅ Sistema de Scraping {self.EMPRESA_NOMBRE} inicializado")
        self.log(f"📂 Directorio de trabajo: {BASE_DIR}")
        if self.log_file:
            log_path = self.log_file.name
            self.log(f"📝 Log guardado en: {log_path}")
        self.log(f"📊 Facturas cargadas: {len(self.df)} registros")
        self.log(f"🔄 Scraping automático cada {self.SCRAPING_INTERVAL} segundos")
        self.log(f"🎯 Intervalo configurado: {self.intervalo_var.get()} segundos")
        self.log("="*50)
        
    def _inicializar_log_file(self):
        """Inicializa el archivo de log con fecha/hora"""
        try:
            # Crear nombre de archivo con fecha y hora
            fecha_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"scraping_log_{fecha_hora}.txt"
            log_path = BASE_DIR / log_filename
            
            # Abrir archivo en modo append (por si se reinicia la app el mismo segundo)
            self.log_file = open(log_path, 'a', encoding='utf-8')
            
            # Escribir encabezado
            self.log_file.write(f"\n{'='*80}\n")
            self.log_file.write(f"SCRAPING LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.log_file.write(f"Directorio: {BASE_DIR}\n")
            self.log_file.write(f"{'='*80}\n\n")
            self.log_file.flush()
            
            print(f"[LOG] Archivo de log creado: {log_path}")
        except Exception as e:
            print(f"[ERROR] No se pudo crear archivo de log: {e}")
            self.log_file = None

    def inicializar_variables(self):
        """Inicializa variables esenciales"""
        self.EMPRESA_NOMBRE = os.getenv('EMPRESA_NOMBRE', 'GUERREROS BURGERS')
        self.SCRAPING_INTERVAL = int(os.getenv('SCRAPING_INTERVAL', 300))  # Intervalo en segundos
        self.SCRAPING_HORA_INICIO = os.getenv('SCRAPING_HORA_INICIO', '08:00')
        self.SCRAPING_HORA_FIN = os.getenv('SCRAPING_HORA_FIN', '20:00')
        self.SCRAPING_DIAS_SEMANA = os.getenv('SCRAPING_DIAS_SEMANA', '0,1,2,3,4,5,6')  # 0=Domingo ... 6=Sábado
        self.SCRAPING_HORAS_PAUSA = os.getenv('SCRAPING_HORAS_PAUSA', '')  # Formato "HH: MM-HH:MM,HH:MM-HH:MM"
        self.SCRAPING_MAX_INTENTOS = int(os.getenv('SCRAPING_MAX_INTENTOS', 3))
        self.SCRAPING_TIEMPO_ESPERA = int(os.getenv('SCRAPING_TIEMPO_ESPERA', 5))
        self.SCRAPING_USUARIO = os.getenv('SCRAPING_USUARIO', '')
        self.SCRAPING_PASSWORD = os.getenv('SCRAPING_PASSWORD', '')
        self.SCRAPING_URL_LOGIN = os.getenv('SCRAPING_URL_LOGIN', 'https://facturacion.electronicacomercial.com/login')
        self.SCRAPING_URL_FACTURAS = os.getenv('SCRAPING_URL_FACTURAS', 'https://facturacion.electronicacomercial.com/facturas')
        self.SCRAPING_CABECERA_API = os.getenv('SCRAPING_CABECERA_API', '')
        self.SCRAPING_TOKEN_API = os.getenv('SCRAPING_TOKEN_API', '')
        self.HEADLESS_MODE = os.getenv('HEADLESS_MODE', '1') == '1'
        
        # ✅ NUEVAS VARIABLES PARA CHECKBOXES
        self.usar_fechas_var = tk.BooleanVar(value=True)
        self.dia_actual_var = tk.BooleanVar(value=True)  # Día actual por defecto
        self.intervalo_var = tk.StringVar(value="60")
        self.reverse_var = tk.BooleanVar(value=False) 
        self.INTERVALO_MINIMO = 30
        
        self.df = pd.DataFrame()
        self.auto_scraping_var = tk.BooleanVar(value=True)
        self.fecha_desde_var = tk.StringVar()
        self.fecha_hasta_var = tk.StringVar()
        self.tree = None
        self.log_textbox = None
        self.total_facturas_var = tk.StringVar(value="0") 
        self.HEADERS = {}
        self.API_TOKEN = None

        # ✅ AGREGAR NUEVAS COLUMNAS AL DATAFRAME
        self.columnas_requeridas = [
            # ✅ COLUMNAS PRINCIPALES DE MAKOS
            'Fecha', 'Prefijo', 'Número', 'Cliente', 'Total', 'SubtotalMakos', 'ImpuestosMakos', 'PropinaMakos',
            
            # ✅ COLUMNAS DE ESTADO Y VALIDACIÓN
            'Estado', 'TNS', 'Validacion', 'ValidacionImpuestos', 'DiferenciaImpuestos', 'Checked',
            
            # ✅ COLUMNAS DE TNS
            'KARDEXID', 'PrefijoTNS', 'NumeroTNS', 'TotalTNS', 'NetoBaseTNS', 'IvaTNS', 'ImpConsumoTNS',
            
            # ✅ COLUMNAS ADICIONALES
            'Teléfono', 'Ubicación', 'Detalles'
        ]

    def inicializar_interfaz(self):
        """Inicializa la interfaz gráfica completa con distribución 75%/25%"""
        self.root.title(f"Sistema de Scraping {self.EMPRESA_NOMBRE}")
        self.root.state('zoomed')
        self.configurar_estilos()

        # Frame principal con paned window para división ajustable
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame izquierdo (75%) - Controles y lista de facturas
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)  # 75% del espacio

        # Frame derecho (25%) - Logs
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)  # 25% del espacio

        # ========== LEFT FRAME (75%) ==========
        self._inicializar_frame_izquierdo(left_frame)

        # ========== RIGHT FRAME (25%) ==========
        self._inicializar_frame_derecho(right_frame)

        # Carga inicial y configuración
        self.cargar_facturas()
        self.programar_scraping_automatico()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _inicializar_frame_izquierdo(self, parent):
        """Inicializa el frame izquierdo con controles y lista de facturas"""
        # Título principal
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(title_frame, text=f"SISTEMA DE SCRAPING - {self.EMPRESA_NOMBRE}", 
                 font=('Helvetica', 16, 'bold'), foreground='#2c3e50').pack()

        # Frame de controles
        controls_frame = ttk.LabelFrame(parent, text=" Controles ", padding="10", relief=tk.GROOVE)
        controls_frame.pack(fill=tk.X, pady=(0, 5))

        # ========== FILA 1: FECHAS ==========
        fecha_frame = ttk.Frame(controls_frame)
        fecha_frame.pack(fill=tk.X, pady=5)

        # Checkbox: Usar día actual (simplificado - reemplaza "Usar fechas")
        self.dia_actual_cb = ttk.Checkbutton(fecha_frame, text="📅 Usar día actual", 
                                            variable=self.dia_actual_var,
                                            command=self.toggle_dia_actual)
        self.dia_actual_cb.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # O: Rango de fechas personalizado
        ttk.Label(fecha_frame, text="O rango personalizado:").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(fecha_frame, text="Desde:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.fecha_desde_var.set((datetime.now() - timedelta(days=self.DIAS_HISTORICO)).strftime('%Y-%m-%d'))
        self.fecha_desde_entry = ttk.Entry(fecha_frame, textvariable=self.fecha_desde_var, width=12)
        self.fecha_desde_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(fecha_frame, text="Hasta:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.fecha_hasta_var.set(datetime.now().strftime('%Y-%m-%d'))
        self.fecha_hasta_entry = ttk.Entry(fecha_frame, textvariable=self.fecha_hasta_var, width=12)
        self.fecha_hasta_entry.grid(row=0, column=5, padx=5, pady=5)

        # ========== FILA 2: HORARIOS Y SCRAPING ==========
        scraping_frame = ttk.Frame(controls_frame)
        scraping_frame.pack(fill=tk.X, pady=5)

        # Horario actual (solo lectura)
        ttk.Label(scraping_frame, text="⏰ Horario:", font=('Helvetica', 9, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.horario_actual_var = tk.StringVar(value="Cargando...")
        self.horario_actual_label = ttk.Label(scraping_frame, textvariable=self.horario_actual_var, 
                                               font=('Helvetica', 9), foreground='#2c3e50', width=50)
        self.horario_actual_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Botón configurar horarios
        self.btn_configurar_horarios = ttk.Button(scraping_frame, text="⚙️ Configurar", 
                                                  command=self.mostrar_configuracion_horarios)
        self.btn_configurar_horarios.grid(row=0, column=2, padx=5, pady=5)
        
        # Checkbox: Scraping automático
        self.auto_scraping_cb = ttk.Checkbutton(scraping_frame, text="🔄 Scraping Automático", 
                                               variable=self.auto_scraping_var,
                                               command=self.toggle_scraping_automatico)
        self.auto_scraping_cb.grid(row=0, column=3, padx=15, pady=5, sticky="w")

        # ========== FILA 3: ACCIONES ==========
        acciones_frame = ttk.Frame(controls_frame)
        acciones_frame.pack(fill=tk.X, pady=5)

        # Botón principal: Ejecutar scraping manual
        self.btn_scraping_manual = ttk.Button(acciones_frame, text="▶️ Ejecutar Scraping Manual", 
                                             command=self.ejecutar_scraping_manual, style='Accent.TButton')
        self.btn_scraping_manual.grid(row=0, column=0, padx=5, pady=5)

        # Separador visual
        ttk.Separator(acciones_frame, orient=tk.VERTICAL).grid(row=0, column=1, padx=10, pady=5, sticky="ns")

        # Botón: Exportar a Excel
        self.btn_exportar_excel = ttk.Button(acciones_frame, text="📤 Exportar a Excel", 
                                            command=self.exportar_a_excel)
        self.btn_exportar_excel.grid(row=0, column=2, padx=5, pady=5)

        # Botones de desarrollo (ocultos por defecto, solo mostrar si es necesario)
        # Se pueden mostrar con Ctrl+Shift+D o similar si se necesita debug
        self.modo_debug = False  # Variable para controlar visibilidad de botones debug
        
        # Actualizar display de horario
        self.actualizar_display_horario()

        # Frame de estadísticas
        stats_frame = ttk.LabelFrame(parent, text=" Estadísticas ", padding="10", relief=tk.GROOVE)
        stats_frame.pack(fill=tk.X, pady=(0, 5))

        self.crear_estadisticas(stats_frame)

        # Frame de lista de facturas (OCUPA EL ESPACIO RESTANTE)
        list_frame = ttk.LabelFrame(parent, text=" Lista de Facturas ", padding="10", relief=tk.GROOVE)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Configurar expansión para que la lista ocupe todo el espacio disponible
        parent.rowconfigure(1, weight=1)

        # Treeview de facturas
        self.crear_treeview(list_frame)

    def _inicializar_frame_derecho(self, parent):
        """Inicializa el frame derecho con el área de logs"""
        # Área de registro - OCUPA TODO EL ESPACIO DISPONIBLE
        log_frame = ttk.LabelFrame(parent, text=" Registro de Actividad ", padding="10", relief=tk.GROOVE)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Configurar el textbox de log para expandirse
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_textbox = scrolledtext.ScrolledText(
            log_frame, 
            width=40,  # Más estrecho para el 25%
            height=8, 
            font=('Consolas', 9), 
            wrap=tk.WORD, 
            state=tk.DISABLED
        )
        self.log_textbox.grid(row=0, column=0, sticky="nsew")

        # Configurar tags para colores
        self.log_textbox.tag_config("success", foreground="green")
        self.log_textbox.tag_config("error", foreground="red")
        self.log_textbox.tag_config("warning", foreground="orange")
        self.log_textbox.tag_config("info", foreground="black")

        # Inicializar estado de checkboxes
        if self.dia_actual_var.get():
            self.toggle_dia_actual()

    def toggle_usar_fechas(self):
        """Activa/desactiva el uso de fechas en las consultas - DEPRECADO (usar toggle_dia_actual)"""
        # Este método se mantiene por compatibilidad pero ya no se usa
        pass

    def toggle_dia_actual(self):
        """Activa/desactiva el uso del día actual para ambas fechas"""
        if self.dia_actual_var.get():
            # Establecer ambas fechas al día actual
            hoy = datetime.now().strftime('%Y-%m-%d')
            self.fecha_desde_var.set(hoy)
            self.fecha_hasta_var.set(hoy)
            
            # Deshabilitar edición manual de fechas
            self.fecha_desde_entry.config(state='disabled')
            self.fecha_hasta_entry.config(state='disabled')
            self.log("📅 Usando día actual para ambas fechas")
            
            # Programar verificación de cambio de día
            self.programar_verificacion_cambio_dia()
        else:
            # Habilitar edición manual de fechas
            self.fecha_desde_entry.config(state='normal')
            self.fecha_hasta_entry.config(state='normal')
            self.log("📅 Usando rango de fechas personalizado")

    def programar_verificacion_cambio_dia(self):
        """Verifica cada minuto si ha cambiado el día y actualiza las fechas si es necesario"""
        if self.dia_actual_var.get():
            hoy_actual = datetime.now().strftime('%Y-%m-%d')
            # Si las fechas no coinciden con el día actual, actualizarlas
            if self.fecha_desde_var.get() != hoy_actual or self.fecha_hasta_var.get() != hoy_actual:
                self.fecha_desde_var.set(hoy_actual)
                self.fecha_hasta_var.set(hoy_actual)
                self.log("🔄 Día cambiado - Fechas actualizadas automáticamente")
        
        # Programar siguiente verificación en 1 minuto (solo si está activo)
        if self.dia_actual_var.get():
            self.root.after(60000, self.programar_verificacion_cambio_dia)

    def mostrar_dialogo_inicio(self):
        """Muestra diálogo al arrancar para elegir modo de inicio"""
        dialog = tk.Toplevel(self.root)
        dialog.title("🚀 Modo de Inicio")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Centrar ventana
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f"500x350+{x}+{y}")
        
        # Frame principal
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(main_frame, text="¿Cómo desea iniciar el sistema?", 
                 font=('Helvetica', 14, 'bold')).pack(pady=(0, 20))
        
        ttk.Label(main_frame, 
                 text="Seleccione el modo de operación para esta sesión:",
                 font=('Helvetica', 10)).pack(pady=(0, 30))
        
        # Opción 1: Automático
        def iniciar_automatico():
            self.auto_scraping_var.set(True)
            self.log("🔄 Modo AUTOMÁTICO activado - Scraping iniciará según horarios configurados")
            self.programar_scraping_automatico()
            dialog.destroy()
        
        btn_auto = ttk.Button(main_frame, text="🔄 Modo Automático", 
                             command=iniciar_automatico, style='Accent.TButton')
        btn_auto.pack(pady=10, padx=20, fill=tk.X)
        ttk.Label(main_frame, 
                 text="Scraping automático según horarios configurados\n"
                      "(12:00 PM - 7:00 PM: cada 4 min | 7:00 PM - 11:59 PM: cada 60 seg)",
                 font=('Helvetica', 9), foreground='#666', justify=tk.CENTER).pack(pady=(0, 15))
        
        # Opción 2: Manual
        def iniciar_manual():
            self.auto_scraping_var.set(False)
            self.log("✋ Modo MANUAL activado - Solo ejecutará cuando presione el botón")
            dialog.destroy()
        
        btn_manual = ttk.Button(main_frame, text="✋ Modo Manual", 
                               command=iniciar_manual)
        btn_manual.pack(pady=10, padx=20, fill=tk.X)
        ttk.Label(main_frame, 
                 text="Solo ejecutará scraping cuando presione 'Ejecutar Scraping Manual'",
                 font=('Helvetica', 9), foreground='#666', justify=tk.CENTER).pack(pady=(0, 15))
        
        # Opción 3: Solo Ver
        def iniciar_solo_ver():
            self.auto_scraping_var.set(False)
            self.log("👁️ Modo SOLO VER activado - Sin scraping automático")
            dialog.destroy()
        
        btn_solo_ver = ttk.Button(main_frame, text="👁️ Solo Ver Datos", 
                                 command=iniciar_solo_ver)
        btn_solo_ver.pack(pady=10, padx=20, fill=tk.X)
        ttk.Label(main_frame, 
                 text="Solo visualizar datos existentes, sin ejecutar scraping",
                 font=('Helvetica', 9), foreground='#666', justify=tk.CENTER).pack(pady=(0, 20))
        
        # Checkbox para recordar preferencia
        recordar_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="💾 Recordar esta preferencia (no preguntar más)", 
                       variable=recordar_var).pack(pady=10)
        
        def guardar_preferencia():
            if recordar_var.get():
                # Guardar preferencia en archivo de configuración
                try:
                    config_path = os.path.join(BASE_DIR, 'inicio_preferencia.txt')
                    modo = "automatico" if self.auto_scraping_var.get() else ("manual" if btn_manual else "solo_ver")
                    with open(config_path, 'w') as f:
                        f.write(modo)
                    self.log(f"💾 Preferencia guardada: {modo}")
                except:
                    pass
        
        # Modificar funciones para guardar preferencia
        def iniciar_auto_con_preferencia():
            self.auto_scraping_var.set(True)
            self.log("🔄 Modo AUTOMÁTICO activado - Scraping iniciará según horarios configurados")
            self.programar_scraping_automatico()
            if recordar_var.get():
                try:
                    config_path = os.path.join(BASE_DIR, 'inicio_preferencia.txt')
                    with open(config_path, 'w') as f:
                        f.write("automatico")
                except:
                    pass
            dialog.destroy()
        
        def iniciar_manual_con_preferencia():
            self.auto_scraping_var.set(False)
            self.log("✋ Modo MANUAL activado - Solo ejecutará cuando presione el botón")
            if recordar_var.get():
                try:
                    config_path = os.path.join(BASE_DIR, 'inicio_preferencia.txt')
                    with open(config_path, 'w') as f:
                        f.write("manual")
                except:
                    pass
            dialog.destroy()
        
        def iniciar_solo_ver_con_preferencia():
            self.auto_scraping_var.set(False)
            self.log("👁️ Modo SOLO VER activado - Sin scraping automático")
            if recordar_var.get():
                try:
                    config_path = os.path.join(BASE_DIR, 'inicio_preferencia.txt')
                    with open(config_path, 'w') as f:
                        f.write("solo_ver")
                except:
                    pass
            dialog.destroy()
        
        # Reemplazar comandos
        btn_auto.config(command=iniciar_auto_con_preferencia)
        btn_manual.config(command=iniciar_manual_con_preferencia)
        btn_solo_ver.config(command=iniciar_solo_ver_con_preferencia)
    
    def cargar_preferencia_inicio(self):
        """Carga la preferencia de inicio guardada"""
        try:
            config_path = os.path.join(BASE_DIR, 'inicio_preferencia.txt')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    modo = f.read().strip()
                    return modo
        except:
            pass
        return None
    
    def actualizar_display_horario(self):
        """Actualiza el display del horario actual en la interfaz"""
        try:
            if hasattr(self, 'gestor_horarios'):
                info = self.gestor_horarios.obtener_info_horario_actual()
                self.horario_actual_var.set(info)
            else:
                self.horario_actual_var.set("No configurado")
        except Exception as e:
            self.horario_actual_var.set(f"Error: {str(e)}")
        
        # Actualizar cada 30 segundos
        if hasattr(self, 'root'):
            self.root.after(30000, self.actualizar_display_horario)
    
    def mostrar_configuracion_horarios(self):
        """Muestra diálogo para configurar horarios de scraping"""
        dialog = tk.Toplevel(self.root)
        dialog.title("⚙️ Configuración de Horarios de Scraping")
        dialog.geometry("700x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Frame principal con scroll
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Configurar Horarios de Scraping", 
                 font=('Helvetica', 14, 'bold')).pack(pady=(0, 20))
        
        ttk.Label(main_frame, 
                 text="El intervalo es el tiempo de descanso DESPUÉS de cada scraping.\n"
                      "Ejemplo: Si un scraping toma 4 minutos y el intervalo es 60 segundos,\n"
                      "el siguiente scraping iniciará 60 segundos después de que termine.",
                 font=('Helvetica', 9), foreground='#666').pack(pady=(0, 20))
        
        # Frame para lista de horarios
        horarios_frame = ttk.LabelFrame(main_frame, text=" Horarios Configurados ", padding="10")
        horarios_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Treeview para mostrar horarios
        columns = ("Hora Inicio", "Hora Fin", "Intervalo", "Estado")
        tree_horarios = ttk.Treeview(horarios_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            tree_horarios.heading(col, text=col)
            tree_horarios.column(col, width=150, anchor=tk.CENTER)
        
        # Cargar horarios actuales
        for horario in self.gestor_horarios.horarios:
            estado = "🟢 ACTIVO" if horario.activo else "🔴 INACTIVO"
            minutos = horario.intervalo_segundos // 60
            segundos = horario.intervalo_segundos % 60
            if minutos > 0:
                intervalo_str = f"{minutos}m {segundos}s" if segundos > 0 else f"{minutos}m"
            else:
                intervalo_str = f"{segundos}s"
            
            tree_horarios.insert("", tk.END, values=(
                horario.hora_inicio.strftime('%H:%M'),
                horario.hora_fin.strftime('%H:%M'),
                intervalo_str,
                estado
            ))
        
        # Scrollbar para treeview
        scrollbar_horarios = ttk.Scrollbar(horarios_frame, orient=tk.VERTICAL, command=tree_horarios.yview)
        tree_horarios.configure(yscrollcommand=scrollbar_horarios.set)
        tree_horarios.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_horarios.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botones para editar/eliminar horarios seleccionados
        acciones_horarios_frame = ttk.Frame(horarios_frame)
        acciones_horarios_frame.pack(fill=tk.X, pady=(5, 0))
        
        def eliminar_horario_seleccionado():
            seleccion = tree_horarios.selection()
            if not seleccion:
                messagebox.showwarning("Advertencia", "Seleccione un horario para eliminar")
                return
            
            item = tree_horarios.item(seleccion[0])
            valores = item['values']
            hora_inicio_str = valores[0]
            hora_fin_str = valores[1]
            
            if messagebox.askyesno("Confirmar", f"¿Eliminar horario {hora_inicio_str} - {hora_fin_str}?"):
                # Buscar y eliminar el horario
                hora_inicio = datetime.strptime(hora_inicio_str, "%H:%M").time()
                hora_fin = datetime.strptime(hora_fin_str, "%H:%M").time()
                
                self.gestor_horarios.horarios = [
                    h for h in self.gestor_horarios.horarios
                    if not (h.hora_inicio == hora_inicio and h.hora_fin == hora_fin)
                ]
                
                self.log(f"✅ Horario eliminado: {hora_inicio_str} - {hora_fin_str}")
                dialog.destroy()
                self.mostrar_configuracion_horarios()  # Refrescar
        
        def editar_horario_seleccionado():
            seleccion = tree_horarios.selection()
            if not seleccion:
                messagebox.showwarning("Advertencia", "Seleccione un horario para editar")
                return
            
            item = tree_horarios.item(seleccion[0])
            valores = item['values']
            hora_inicio_str = valores[0]
            hora_fin_str = valores[1]
            
            # Cargar valores en los campos
            inicio_var.set(hora_inicio_str)
            fin_var.set(hora_fin_str)
            
            # Buscar el horario para obtener intervalo y estado
            hora_inicio = datetime.strptime(hora_inicio_str, "%H:%M").time()
            hora_fin = datetime.strptime(hora_fin_str, "%H:%M").time()
            
            for h in self.gestor_horarios.horarios:
                if h.hora_inicio == hora_inicio and h.hora_fin == hora_fin:
                    intervalo_var.set(str(h.intervalo_segundos))
                    activo_var.set(h.activo)
                    break
            
            # Eliminar el horario seleccionado (se agregará de nuevo con los nuevos valores)
            self.gestor_horarios.horarios = [
                h for h in self.gestor_horarios.horarios
                if not (h.hora_inicio == hora_inicio and h.hora_fin == hora_fin)
            ]
            
            messagebox.showinfo("Editar Horario", 
                f"Horario cargado en los campos.\n"
                f"Modifique los valores y haga clic en 'Agregar Horario' para guardar los cambios.")
        
        ttk.Button(acciones_horarios_frame, text="✏️ Editar Seleccionado", 
                  command=editar_horario_seleccionado).pack(side=tk.LEFT, padx=5)
        ttk.Button(acciones_horarios_frame, text="🗑️ Eliminar Seleccionado", 
                  command=eliminar_horario_seleccionado).pack(side=tk.LEFT, padx=5)
        
        # Frame para agregar nuevo horario
        nuevo_frame = ttk.LabelFrame(main_frame, text=" Agregar/Editar Horario ", padding="10")
        nuevo_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(nuevo_frame, text="Hora Inicio (HH:MM):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        inicio_var = tk.StringVar(value="12:00")
        ttk.Entry(nuevo_frame, textvariable=inicio_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(nuevo_frame, text="Hora Fin (HH:MM):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        fin_var = tk.StringVar(value="19:00")
        ttk.Entry(nuevo_frame, textvariable=fin_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(nuevo_frame, text="Intervalo (segundos):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        intervalo_var = tk.StringVar(value="240")
        ttk.Entry(nuevo_frame, textvariable=intervalo_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        activo_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(nuevo_frame, text="Activo", variable=activo_var).grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        def validar_formato_hora(hora_str):
            """Valida formato HH:MM"""
            try:
                partes = hora_str.split(':')
                if len(partes) != 2:
                    return False, "Formato debe ser HH:MM (ej: 12:00)"
                hora = int(partes[0])
                minuto = int(partes[1])
                if hora < 0 or hora > 23:
                    return False, "Hora debe estar entre 00 y 23"
                if minuto < 0 or minuto > 59:
                    return False, "Minuto debe estar entre 00 y 59"
                return True, None
            except:
                return False, "Formato inválido. Use HH:MM (ej: 12:00)"
        
        def validar_rangos_consecutivos():
            """Valida que los horarios cubran todo el día sin gaps grandes"""
            horarios_ordenados = sorted(self.gestor_horarios.horarios, key=lambda h: h.hora_inicio)
            gaps = []
            
            # Verificar desde medianoche
            if horarios_ordenados and horarios_ordenados[0].hora_inicio > dt_time(0, 0):
                gaps.append(f"Gap desde 00:00 hasta {horarios_ordenados[0].hora_inicio.strftime('%H:%M')}")
            
            # Verificar entre horarios
            for i in range(len(horarios_ordenados) - 1):
                fin_actual = horarios_ordenados[i].hora_fin
                inicio_siguiente = horarios_ordenados[i + 1].hora_inicio
                
                # Calcular diferencia (manejar cruce de medianoche)
                if fin_actual <= inicio_siguiente:
                    # No cruza medianoche
                    if (inicio_siguiente.hour * 60 + inicio_siguiente.minute) - (fin_actual.hour * 60 + fin_actual.minute) > 1:
                        gaps.append(f"Gap desde {fin_actual.strftime('%H:%M')} hasta {inicio_siguiente.strftime('%H:%M')}")
                else:
                    # Cruza medianoche - verificar gap al final del día
                    minutos_hasta_medianoche = (23 - fin_actual.hour) * 60 + (59 - fin_actual.minute)
                    minutos_desde_medianoche = inicio_siguiente.hour * 60 + inicio_siguiente.minute
                    if minutos_hasta_medianoche + minutos_desde_medianoche > 1:
                        gaps.append(f"Gap desde {fin_actual.strftime('%H:%M')} hasta {inicio_siguiente.strftime('%H:%M')} (cruza medianoche)")
            
            # Verificar hasta medianoche
            if horarios_ordenados and horarios_ordenados[-1].hora_fin < dt_time(23, 59):
                gaps.append(f"Gap desde {horarios_ordenados[-1].hora_fin.strftime('%H:%M')} hasta 23:59")
            
            return gaps
        
        def agregar_horario():
            try:
                inicio = inicio_var.get().strip()
                fin = fin_var.get().strip()
                intervalo_str = intervalo_var.get().strip()
                activo = activo_var.get()
                
                # ✅ VALIDACIÓN 1: Formato de hora inicio
                valido, error = validar_formato_hora(inicio)
                if not valido:
                    messagebox.showerror("Error de Validación", f"Hora de inicio: {error}")
                    return
                
                # ✅ VALIDACIÓN 2: Formato de hora fin
                valido, error = validar_formato_hora(fin)
                if not valido:
                    messagebox.showerror("Error de Validación", f"Hora de fin: {error}")
                    return
                
                # ✅ VALIDACIÓN 3: Intervalo positivo
                try:
                    intervalo = int(intervalo_str)
                    if intervalo <= 0:
                        messagebox.showerror("Error de Validación", "El intervalo debe ser mayor que 0")
                        return
                except ValueError:
                    messagebox.showerror("Error de Validación", "El intervalo debe ser un número entero")
                    return
                
                # ✅ VALIDACIÓN 4: Hora inicio < hora fin (si no cruza medianoche)
                inicio_time = datetime.strptime(inicio, "%H:%M").time()
                fin_time = datetime.strptime(fin, "%H:%M").time()
                
                if inicio_time == fin_time:
                    messagebox.showerror("Error de Validación", "La hora de inicio y fin no pueden ser iguales")
                    return
                
                # Agregar horario
                self.gestor_horarios.agregar_horario(inicio, fin, intervalo, activo)
                
                # ✅ VALIDACIÓN 5: Verificar gaps (solo advertencia, no bloquea)
                gaps = validar_rangos_consecutivos()
                if gaps:
                    respuesta = messagebox.askyesno(
                        "Advertencia - Gaps Detectados",
                        f"Se detectaron gaps en la cobertura:\n\n" + "\n".join(f"  • {gap}" for gap in gaps) +
                        "\n\nEl programa funcionará, pero algunas horas pueden usar valores por defecto.\n\n"
                        "¿Desea continuar de todos modos?"
                    )
                    if not respuesta:
                        # Remover el horario recién agregado
                        self.gestor_horarios.horarios = [h for h in self.gestor_horarios.horarios 
                                                         if not (h.hora_inicio == inicio_time and h.hora_fin == fin_time)]
                        return
                
                self.log(f"✅ Horario agregado: {inicio}-{fin}, Intervalo: {intervalo}s, Activo: {activo}")
                if gaps:
                    self.log(f"⚠️ Advertencia: Se detectaron gaps en la cobertura")
                self.log(f"ℹ️ Los cambios se aplicarán al siguiente scraping (el actual no se interrumpe)")
                messagebox.showinfo("Éxito", 
                    f"Horario agregado correctamente.\n\n"
                    f"Los cambios se aplicarán automáticamente al siguiente scraping.\n"
                    f"El scraping actual (si está corriendo) NO se interrumpe.")
                dialog.destroy()
                self.mostrar_configuracion_horarios()  # Refrescar
            except ValueError as e:
                messagebox.showerror("Error de Validación", f"Error en formato de hora: {str(e)}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al agregar horario: {str(e)}")
        
        ttk.Button(nuevo_frame, text="➕ Agregar Horario", command=agregar_horario).grid(row=1, column=3, padx=5, pady=5)
        
        # Botones de acción
        botones_frame = ttk.Frame(main_frame)
        botones_frame.pack(fill=tk.X)
        
        def restaurar_defecto():
            if messagebox.askyesno("Confirmar", "¿Restaurar horarios por defecto?\n"
                                "12:01 AM - 12:00 PM: INACTIVO\n"
                                "12:00 PM - 7:00 PM: cada 4 minutos\n"
                                "7:00 PM - 11:59 PM: cada 60 segundos"):
                self.gestor_horarios.limpiar_horarios()
                self.gestor_horarios._cargar_horarios_por_defecto()
                self.log("✅ Horarios restaurados a valores por defecto")
                dialog.destroy()
                self.mostrar_configuracion_horarios()
        
        ttk.Button(botones_frame, text="🔄 Restaurar Por Defecto", command=restaurar_defecto).pack(side=tk.LEFT, padx=5)
        ttk.Button(botones_frame, text="✅ Cerrar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def crear_estadisticas(self, parent):
        """Crea el panel de estadísticas"""
        # Frame para estadísticas
        stats_container = ttk.Frame(parent)
        stats_container.pack(fill=tk.X)

        # Variables para estadísticas
        self.total_facturas_var = tk.StringVar(value="0")
        self.facturas_hoy_var = tk.StringVar(value="0")
        self.facturas_insertadas_var = tk.StringVar(value="0")
        self.estado_sistema_var = tk.StringVar(value="Conectado")

        # Estadísticas
        stats = [
            ("Total Facturas:", self.total_facturas_var),
            ("Facturas Hoy:", self.facturas_hoy_var),
            ("Insertadas en TNS:", self.facturas_insertadas_var),
            ("Estado:", self.estado_sistema_var)
        ]

        for i, (label, var) in enumerate(stats):
            ttk.Label(stats_container, text=label, font=('Helvetica', 10, 'bold')).grid(row=0, column=i*2, padx=10, pady=5)
            ttk.Label(stats_container, textvariable=var, font=('Helvetica', 10), 
                     foreground='#2c3e50').grid(row=0, column=i*2+1, padx=5, pady=5)

    def crear_treeview(self, parent):
        """Crea el treeview para mostrar las facturas CON ORDEN CORRECTO"""
        # ✅ COLUMNAS EN EL ORDEN EXACTO QUE QUEREMOS
        columns = (
            "Fecha", "Prefijo", "Número", "Cliente", "Total", "Subtotal", "Impuestos", "Propina",
            "Estado", "TNS", "Validacion", "ValidacionImpuestos", "DiferenciaImpuestos",
            "KARDEXID", "PrefijoTNS", "NumeroTNS", "TotalTNS", "NetoBaseTNS", "IvaTNS", "ImpConsumoTNS"
        )

        self.tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)

        # Configurar columnas
        column_config = {
            "Fecha": {"width": 150, "anchor": tk.W, "text": "📅 Fecha"},
            "Prefijo": {"width": 150, "anchor": tk.CENTER, "text": "🏷️ Prefijo Makos"},
            "Número": {"width": 120, "anchor": tk.CENTER, "text": "# Número Makos"},
            "Cliente": {"width": 200, "anchor": tk.W, "text": "👤 Cliente"},
            "Total": {"width": 110, "anchor": tk.CENTER, "text": "💰 Total Makos"},
            "Subtotal": {"width": 150, "anchor": tk.CENTER, "text": "📊 Subtotal Makos"},
            "Impuestos": {"width":150, "anchor": tk.CENTER, "text": "🧾 Impuestos Makos"},
            "Propina": {"width": 150, "anchor": tk.CENTER, "text": "💵 Propina Makos"},
            "Estado": {"width": 120, "anchor": tk.CENTER, "text": "📈 Estado"},
            "TNS": {"width": 80, "anchor": tk.CENTER, "text": "🔗 TNS"},
            "Validacion": {"width": 100, "anchor": tk.CENTER, "text": "✅ Validación Total"},
            "ValidacionImpuestos": {"width": 180, "anchor": tk.CENTER, "text": "📋 Validación Impuestos"},
            "DiferenciaImpuestos": {"width": 180, "anchor": tk.CENTER, "text": "⚖️ Diferencia Impuestos"},
            "KARDEXID": {"width": 100, "anchor": tk.CENTER, "text": "🔑 KARDEXID"},
            "PrefijoTNS": {"width": 150, "anchor": tk.CENTER, "text": "🏷️ Prefijo TNS"},
            "NumeroTNS": {"width": 100, "anchor": tk.CENTER, "text": "# Número TNS"},
            "TotalTNS": {"width": 100, "anchor": tk.CENTER, "text": "💰 Total TNS"},
            "NetoBaseTNS": {"width": 150, "anchor": tk.CENTER, "text": "📦 Neto Base TNS"},
            "IvaTNS": {"width": 100, "anchor": tk.CENTER, "text": "🏛️ IVA TNS"},
            "ImpConsumoTNS": {"width": 200, "anchor": tk.CENTER, "text": "🍽️ Imp. Consumo TNS"}
        }

        for col, config in column_config.items():
            self.tree.column(col, width=config["width"], anchor=config["anchor"])
            self.tree.heading(col, text=config["text"])  # ✅ USAR NOMBRES BONITOS

        # Scrollbars
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Configurar expansión
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)


    def configurar_estilos(self):
        """Configura estilos modernos para la interfaz reorganizada"""
        estilo = ttk.Style()
        estilo.theme_use('clam')

        # Configurar colores modernos
        estilo.configure('.', background='#f8f9fa', foreground='#2c3e50')
        estilo.configure('TFrame', background='#f8f9fa')
        estilo.configure('TLabel', background='#f8f9fa', foreground='#2c3e50', font=('Helvetica', 10))
        estilo.configure('TLabelframe', background='#f8f9fa', relief=tk.GROOVE, borderwidth=2)
        estilo.configure('TLabelframe.Label', background='#f8f9fa', foreground='#2c3e50', font=('Helvetica', 11, 'bold'))

        # Botones modernos
        estilo.configure('TButton', font=('Helvetica', 10), background='#3498db', foreground='white')
        estilo.map('TButton', background=[('active', '#2980b9')])

        # Botón acentuado
        estilo.configure('Accent.TButton', background='#27ae60', foreground='white')
        estilo.map('Accent.TButton', background=[('active', '#219653')])

        # Treeview moderno
        estilo.configure('Treeview', font=('Helvetica', 9), rowheight=25, background='white', fieldbackground='white')
        estilo.configure('Treeview.Heading', font=('Helvetica', 10, 'bold'), background='#34495e', foreground='white')

        # PanedWindow style
        estilo.configure('TPanedwindow', background='#f8f9fa')

    def verificar_archivos_iniciales(self):
        """Verifica y carga archivos esenciales (.env y Excel)"""
        try:
            # 1. Verificar .env
            env_path = os.path.join(BASE_DIR, ".env")
            if not os.path.exists(env_path):
                raise FileNotFoundError(f"No se encontró el archivo .env en {env_path}")

            # 2. Cargar configuración del .env
            load_dotenv(env_path)
            excel_file = os.getenv("EXCEL_FILE", "Facturas_Guerreros.xlsx")
            self.EXCEL_FILE = os.path.join(BASE_DIR, excel_file)

            # 3. Inicializar DataFrame con estructura completa (igual que antes)
            columnas = ['Prefijo', 'Número', 'Fecha', 'Cliente', 'Total', 'Estado', 
                       'Teléfono', 'Ubicación', 'Checked', 'Detalles', 'TNS',
                       'KARDEXID', 'TotalTNS', 'Validacion'] 
            self.df = pd.DataFrame(columns=columnas)

            # 4. ✅ MIGRACIÓN: Si existe Excel, marcar para migrar después
            # Nota: La migración real se hará cuando self.db y self.log estén disponibles
            if os.path.exists(self.EXCEL_FILE):
                self._excel_existe = True
                self.df = pd.DataFrame(columns=columnas)
            else:
                self._excel_existe = False
                self.df = pd.DataFrame(columns=columnas)

        except Exception as e:
            self.log(f"❌ Error crítico: {str(e)}")
            messagebox.showerror("Error", f"No se pudo iniciar la aplicación:\n{str(e)}")
            self.root.destroy()
            sys.exit(1)

    def cargar_configuracion(self):
        """Carga la configuración desde el archivo .env"""
        env_path = os.path.join(BASE_DIR, '.env')
        load_dotenv(env_path, override=True)

        # Configuración aplicación
        self.EMPRESA_NOMBRE = os.getenv('EMPRESA_NOMBRE', 'Empresa')
        self.EXCEL_FILE = os.path.join(BASE_DIR, os.getenv('EXCEL_FILE', 'Facturas_Guerreros.xlsx'))
        
        # Configuración web
        self.BASE_URL = os.getenv('WEB_BASE_URL', '')
        self.LOGIN_URL = self.BASE_URL + os.getenv('WEB_LOGIN_PATH', '')
        self.INVOICE_URL = self.BASE_URL + os.getenv('WEB_INVOICE_PATH', '')
        
        self.CREDENTIALS = {
            'username': os.getenv('WEB_USERNAME', ''),
            'password': os.getenv('WEB_PASSWORD', ''),
            'ip': os.getenv('IP', '143.105.99.221'),  # ✅ Corregido: 'ip' en minúsculas para coincidir con el uso
            'device': os.getenv('DEVICE', 'desktop'),  # Si es necesario
        }
        
        # Configuración de scraping
        self.DIAS_HISTORICO = int(os.getenv('DIAS_HISTORICO', 2))
        self.SCRAPING_INTERVAL = int(os.getenv('SCRAPING_INTERVAL', 300))

    def programar_scraping_automatico(self):
        """
        Ejecuta el scraping automáticamente con horarios variables
        El intervalo se actualiza automáticamente según la hora del día
        """
        try:
            if not self.auto_scraping_var.get():
                # Si scraping automático está desactivado, revisar cada minuto
                self.root.after(60000, self.programar_scraping_automatico)
                return

            # ✅ OBTENER INTERVALO SEGÚN HORA ACTUAL
            intervalo, activo, descripcion = self.gestor_horarios.obtener_intervalo_actual()
            
            # Actualizar el campo de intervalo visualmente (solo para mostrar)
            self.intervalo_var.set(str(intervalo))
            
            # ✅ DETECTAR CAMBIO DE HORARIO (activo ↔ inactivo)
            if self.horario_anterior_activo is not None and self.horario_anterior_activo != activo:
                # Hubo un cambio de horario
                if not activo:
                    # Cambió a INACTIVO: hacer logout para cerrar sesión
                    self.log(f"🔄 Cambio de horario detectado: ACTIVO → INACTIVO")
                    self.log(f"🔓 Haciendo logout para evitar caducidad del token durante periodo inactivo...")
                    self.hacer_logout()
                else:
                    # Cambió a ACTIVO: renovar sesión (logout + login) para obtener token fresco
                    self.log(f"🔄 Cambio de horario detectado: INACTIVO → ACTIVO")
                    self.log(f"🔄 Renovando sesión para obtener token fresco...")
                    self.renovar_sesion()
            
            # Actualizar estado anterior
            self.horario_anterior_activo = activo
            
            # ✅ RENOVACIÓN PERIÓDICA DE SESIÓN (cada hora durante horario activo)
            if activo:
                ahora = time.time()
                if (self.ultima_renovacion_sesion is None or 
                    ahora - self.ultima_renovacion_sesion >= self.INTERVALO_RENOVACION_SESION):
                    self.log(f"🔄 Renovación periódica de sesión (cada {self.INTERVALO_RENOVACION_SESION // 60} minutos)...")
                    if self.renovar_sesion():
                        self.ultima_renovacion_sesion = ahora
                    else:
                        self.log("⚠️ No se pudo renovar sesión, se intentará en el próximo ciclo")
            
            # ✅ VERIFICAR SI ESTÁ ACTIVO EN ESTE HORARIO
            if not activo:
                # Horario inactivo (ej: madrugada)
                hora_actual = datetime.now().strftime('%H:%M')
                self.log(f"⏸️ Horario INACTIVO ({descripcion}) - Hora actual: {hora_actual}")
                # Revisar cada minuto para detectar cambio de horario
                self.root.after(60000, self.programar_scraping_automatico)
                return

            estado = self.scraping_manager.get_estado_detallado()
            
            # Log solo cada 5 minutos para no saturar
            tiempo_desde_fin = estado['tiempo_desde_fin']
            # Verificar que no sea infinito antes de convertir a int
            if tiempo_desde_fin != float('inf') and tiempo_desde_fin < 1e10:
                if int(tiempo_desde_fin) % 300 < 30:
                    info_horario = self.gestor_horarios.obtener_info_horario_actual()
                    self.log(f"⏰ {info_horario} | Tiempo desde último: {tiempo_desde_fin:.0f}s")

            # ✅ LÓGICA: Solo ejecutar si no está activo Y ha pasado el intervalo
            tiempo_desde_fin = estado['tiempo_desde_fin']
            # Si es infinito (nunca se ha ejecutado), permitir ejecutar
            puede_ejecutar = (tiempo_desde_fin == float('inf') or tiempo_desde_fin >= intervalo)
            if not estado['scraping_activo'] and puede_ejecutar:
                self.log(f"🚀 Iniciando scraping automático (Horario: {descripcion}, Intervalo: {intervalo}s)")
                self.scraping_manager.scraping_automatico(self.ejecutar_scraping)

            # ✅ REVISAR cada 30 segundos (para detectar cambios de horario rápidamente)
            # Si el intervalo cambia, se aplicará en la siguiente revisión
            self.root.after(30000, self.programar_scraping_automatico)

        except Exception as e:
            self.log(f"❌ Error en programar_scraping_automatico: {str(e)}")
            import traceback
            self.log(f"🔍 Detalle: {traceback.format_exc()}")
            self.root.after(30000, self.programar_scraping_automatico)
            
    def debug_estado_scraping(self):
        """Debug completo del estado del scraping"""
        estado = f"""
            🔧 DEBUG COMPLETO - {datetime.now().strftime('%H:%M:%S')}
            • scraping_activo: {self.scraping_manager.scraping_activo}
            • scraping_pendiente: {self.scraping_manager.scraping_pendiente}
            • ultimo_tiempo_fin: {self.scraping_manager.ultimo_tiempo_fin}
            • tiempo_desde_fin: {self.scraping_manager.tiempo_desde_ultimo_fin():.0f}s
            • Intervalo configurado: {self.intervalo_var.get()}s
            • Auto scraping: {self.auto_scraping_var.get()}
            • Hilos activos: {threading.active_count()}
                """
        self.log(estado)

    def _ejecutar_scraping_con_callback(self, scraping_function, callback):
        """Ejecuta scraping y llama al callback cuando termina TODO el proceso"""
        try:
            # Usar el manager para el scraping automático
            self.scraping_manager.scraping_automatico(scraping_function)
        except Exception as e:
            self.log(f"❌ Error en scraping: {str(e)}")
        finally:
            # ✅ Llamar al callback para programar siguiente (incluso si hay error)
            # Esto asegura que "terminar scraping" incluye validaciones e inserciones TNS
            if callback:
                self.root.after(0, callback)  # Ejecutar en el hilo principal
    
    def toggle_scraping_automatico(self):
        """Activa/desactiva el scraping automático"""
        if self.auto_scraping_var.get():
            self.log("✅ Scraping automático ACTIVADO")
            # ✅ Iniciar el proceso de scraping automático si está activado
            self.programar_scraping_automatico()
        else:
            self.log("❌ Scraping automático DESACTIVADO")
            # No hacer nada si está desactivado (programar_scraping_automatico ya verifica esto)
    
    def exportar_a_excel(self):
        """Exporta las facturas desde SQLite a Excel"""
        try:
            from tkinter import filedialog
            
            # Pedir ruta donde guardar
            excel_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=f"Facturas_Makos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                title="Guardar Excel como..."
            )
            
            if not excel_path:
                self.log("ℹ️ Exportación cancelada por el usuario")
                return
            
            # Verificar que db esté inicializado
            if not hasattr(self, 'db') or self.db is None:
                self.db = MakosDatabase(log_callback=self.log)
            
            # Exportar usando el método de makos_db
            if self.db.exportar_a_excel(excel_path):
                self.log(f"✅ Exportación exitosa: {excel_path}")
                messagebox.showinfo("Éxito", 
                    f"Facturas exportadas correctamente a:\n{excel_path}\n\n"
                    f"Total: {len(self.df)} facturas")
            else:
                self.log(f"❌ Error en la exportación")
                messagebox.showerror("Error", "No se pudo exportar a Excel")
                
        except Exception as e:
            self.log(f"❌ Error exportando a Excel: {str(e)}")
            import traceback
            self.log(f"🔍 Detalle: {traceback.format_exc()}")
            messagebox.showerror("Error", f"Error al exportar:\n{str(e)}")
     
    def ver_estado_scraping(self):
        """Muestra el estado actual del scraping"""
        try:
            tiempo_desde_fin = self.scraping_manager.tiempo_desde_ultimo_fin()

            estado = f"""
                📊 ESTADO SCRAPING - {datetime.now().strftime('%H:%M:%S')}

                • 🟢 Scraping ACTIVO: {'✅ SÍ' if self.scraping_manager.scraping_activo else '❌ NO'}
                • 🟡 En COLA: {'✅ SÍ' if self.scraping_manager.scraping_pendiente else '❌ NO'}  
                • ⏰ Último fin: {tiempo_desde_fin:.0f}s atrás
                • 🎯 Intervalo: {self.intervalo_var.get()}s
                • 🤖 Automático: {'✅ ACTIVADO' if self.auto_scraping_var.get() else '❌ DESACTIVADO'}

                💡 Comandos debug:
                   app.debug_estado_scraping()
                   app.scraping_manager.reset_estado()
                        """
            self.log(estado)

        except Exception as e:
            self.log(f"❌ Error obteniendo estado: {str(e)}")

    def ejecutar_scraping_manual(self):
        """Ejecuta el scraping de forma manual - VERSIÓN CORREGIDA"""
        self.log("\n🔍 SOLICITANDO SCRAPING MANUAL...")

        # ✅ USAR DIRECTAMENTE EL MÉTODO DEL MANAGER
        resultado = self.scraping_manager.scraping_manual(self.ejecutar_scraping)

        if resultado:
            self.log("▶️ Scraping manual iniciado correctamente")
        else:
            self.log("⏳ Scraping manual en cola (ya hay uno activo)")

        return resultado
    
    def ejecutar_scraping(self):
        """Proceso completo de scraping con validación de datos TNS"""
        self.log("\n" + "="*50)
        self.log("🔍 INICIANDO PROCESO DE SCRAPING - VALIDACIÓN TNS COMPLETA")
        self.log("="*50)

        try:
            # 1. AUTENTICACIÓN
            if not self.smart_login():
                raise Exception("No se pudo autenticar")

            # 2. ✅ MEJORADO: VERIFICAR Y VALIDAR FACTURAS EXISTENTES EN EXCEL (CONSULTA MASIVA)
            facturas_a_validar = self._obtener_facturas_por_rango()
            if facturas_a_validar:
                self.log(f"🔄 Validando {len(facturas_a_validar)} facturas del Excel contra TNS (CONSULTA MASIVA)")
                # ✅ USAR VALIDACIÓN MASIVA EN LUGAR DE INDIVIDUAL
                self._validar_lote_facturas_tns(facturas_a_validar)

            # 3. OBTENER NUEVAS FACTURAS DE MAKOS
            self.log("\n📡 Obteniendo facturas nuevas desde Makos...")
            facturas_makos = self._obtener_facturas_api()

            if not facturas_makos:
                self.log("ℹ️ No se encontraron facturas nuevas en Makos")
                self.actualizar_interfaz_despues_scraping()
                return True

            # 4. PROCESAR NUEVAS FACTURAS (individual como antes)
            nuevas_procesadas = 0
            for idx, factura_makos in enumerate(facturas_makos, 1):
                try:
                    prefijo_makos = factura_makos.get('prefix', '')
                    numero_makos = str(factura_makos.get('number', ''))

                    # Verificar si ya existe en Excel
                    if self._factura_existe(prefijo_makos, numero_makos):
                        self.log(f"ℹ️ Ya existe en Excel: {prefijo_makos}-{numero_makos}")
                        continue
                    
                    if self._procesar_factura_nueva(factura_makos):
                        nuevas_procesadas += 1

                except Exception as e:
                    self.log(f"⚠️ Error en factura {idx}: {str(e)}")
                    continue

            # 5. RESULTADOS
            self.log("\n" + "="*50)
            self.log("📊 RESUMEN DEL SCRAPING")
            self.log(f"✅ Facturas validadas: {len(facturas_a_validar)}")
            self.log(f"✅ Facturas nuevas procesadas: {nuevas_procesadas}")
            self.log(f"📂 Total en Excel: {len(self.df)}")

            # 6. GUARDAR SQLite UNA SOLA VEZ al final (más eficiente)
            if nuevas_procesadas > 0 or len(facturas_a_validar) > 0:
                if self.guardar_excel():
                    self.log(f"💾 SQLite guardado: {len(self.df)} registros")
            
            # 7. ACTUALIZAR INTERFAZ
            self.actualizar_interfaz_despues_scraping()
            return True

        except Exception as e:
            self.log(f"❌ ERROR CRÍTICO: {str(e)}")
            return False    
    
    def _procesar_factura_nueva(self, factura_makos):
        """Procesa una factura nueva de Makos con validación TNS COMPLETA - VERSIÓN CORREGIDA"""
        
        prefijo_makos = factura_makos.get('prefix', '')
        numero_makos = str(factura_makos.get('number', ''))
        factura_id = f"{prefijo_makos}-{numero_makos}"

        # ✅ VERIFICACIÓN EN MEMORIA
        with self.processing_lock:
            if factura_id in self.facturas_procesando:
                self.log(f"🔄 Ya procesando: {factura_id}")
                return False
            self.facturas_procesando.add(factura_id)
        
        try:
            prefijo_makos = factura_makos.get('prefix', '')
            numero_makos = str(factura_makos.get('number', ''))
    
            # Obtener detalles de Makos
            self.log(f"🔍 Obteniendo detalles de Makos: {prefijo_makos}-{numero_makos}")
            
            detalle_completo = self._get_detalle_factura_api(factura_makos)

            if not detalle_completo or not detalle_completo.get('items'):
                self.log(f"❌ No se pudieron obtener detalles de Makos después de múltiples intentos")
                return False
    
            # ✅ Preparar fecha y hora combinadas desde el endpoint
            fecha_str = factura_makos.get('datedoc', '')
            hora_str = factura_makos.get('hourdoc', '00:00')
            
            try:
                if fecha_str:
                    # Combinar fecha y hora: "21/11/2025" + "20:50" = "21/11/2025 20:50"
                    fecha_hora_str = f"{fecha_str} {hora_str}"
                    # Parsear con formato: día/mes/año hora:minuto
                    fecha_dt = datetime.strptime(fecha_hora_str, '%d/%m/%Y %H:%M')
                else:
                    fecha_dt = datetime.now()
            except Exception as e:
                # Si falla el parseo, intentar solo con fecha
                try:
                    if fecha_str:
                        fecha_dt = datetime.strptime(fecha_str, '%d/%m/%Y')
                    else:
                        fecha_dt = datetime.now()
                except:
                    # Si todo falla, usar fecha/hora actual
                    fecha_dt = datetime.now()
    
            # ✅ **PASO CRÍTICO CORREGIDO: Siempre validar en TNS aunque no esté en Excel**
            existe_en_tns, kardexid, total_tns, netobase_tns, netoiva_tns, vriconsumo_tns, prefijo_tns, numero_tns = self.firebird.factura_existe(prefijo_makos, numero_makos)
    
            # ✅ OBTENER DATOS DE IMPUESTOS Y PROPINA DE MAKOS
            subtotal_makos = float(factura_makos.get('subtotal', 0))
            impuestos_makos = float(factura_makos.get('impuestos', 0))
            propina_makos = float(factura_makos.get('tip', 0))
            total_makos = float(factura_makos.get('total', 0)) + propina_makos
            # si el valor de enabled es 1 la factura está activa
            factura_activa = factura_makos.get('enabled', 1) == 1
            
            # ✅ CALCULAR DIFERENCIA EXACTA
            impuestos_tns = netoiva_tns + vriconsumo_tns if existe_en_tns else 0
            diferencia_impuestos = impuestos_makos - impuestos_tns  # ✅ DIFERENCIA EXACTA
    
            # ✅ **NUEVA LÓGICA: Validación completa independientemente de si está en Excel**
            if existe_en_tns:
                # ✅ APLICAR LA MISMA LÓGICA FLEXIBLE QUE EN _validar_factura_con_tns
                totales_coinciden = abs(total_makos - total_tns) < 0.01
    
                if totales_coinciden:
                    impuestos_coinciden = abs(diferencia_impuestos) <= 1.00
                else:
                    impuestos_coinciden = abs(diferencia_impuestos) < 0.01
    
                estado = 'TNS_VALIDADO' if totales_coinciden else 'TNS_ERROR_TOTAL'
                validacion_total = 'OK' if totales_coinciden else 'ERROR'
                validacion_impuestos = 'OK' if impuestos_coinciden else 'ERROR'
    
                self.log(f"✅ Factura EXISTE en TNS: {prefijo_makos}-{numero_makos}")
                if totales_coinciden:
                    if impuestos_coinciden:
                        self.log(f"   💰 Validación COMPLETA OK: Total Makos ${total_makos:,.2f} = TNS ${total_tns:,.2f}")
                        self.log(f"   📊 Impuestos: Makos ${impuestos_makos:,.2f} = TNS ${impuestos_tns:,.2f}")
                    else:
                        self.log(f"⚠️ Validación PARCIAL: Total OK pero impuestos con diferencia de ${diferencia_impuestos:,.2f}")
                else:
                    self.log(f"❌ ERROR Validación: Total Makos ${total_makos:,.2f} ≠ TNS ${total_tns:,.2f}")
    
            else:
                # No existe en TNS
                estado = 'PENDIENTE_TNS'
                validacion_total = 'PENDIENTE'
                validacion_impuestos = 'PENDIENTE'
                self.log(f"❌ No existe en TNS: {prefijo_makos}-{numero_makos}")
    
            # Crear nueva fila con TODAS las columnas (CON VALORES CORRECTOS SEGÚN VALIDACIÓN TNS)
            new_row = {
                'Prefijo': prefijo_makos,
                'Número': numero_makos,
                'Fecha': fecha_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'Cliente': factura_makos.get('alias', ''),
                'Total': total_makos,
                # ✅ NUEVOS CAMPOS DE MAKOS
                'SubtotalMakos': subtotal_makos,
                'ImpuestosMakos': impuestos_makos,
                'PropinaMakos': propina_makos,
    
                'Teléfono': detalle_completo.get('phone', ''),
                'Ubicación': detalle_completo.get('address', ''),
                'Estado': estado,
                'Checked': '',
                'Detalles': json.dumps(detalle_completo, ensure_ascii=False),
                'TNS': 'SÍ' if existe_en_tns else 'NO',
                'KARDEXID': kardexid if existe_en_tns else '',
                'TotalTNS': total_tns if existe_en_tns else 0,
                'Validacion': validacion_total,
    
                # ✅ NUEVOS CAMPOS DE IMPUESTOS TNS
                'NetoBaseTNS': netobase_tns if existe_en_tns else 0,
                'IvaTNS': netoiva_tns if existe_en_tns else 0,
                'ImpConsumoTNS': vriconsumo_tns if existe_en_tns else 0,
                'ValidacionImpuestos': validacion_impuestos,
                'DiferenciaImpuestos': diferencia_impuestos,
                'PrefijoTNS': prefijo_tns if existe_en_tns else '',
                'NumeroTNS': numero_tns if existe_en_tns else ''
            }
    
            # Insertar en DataFrame      with self.df_lock:
            with self.df_lock:
                nueva_fila_df = pd.DataFrame([new_row])
    
                # Asegurar que todas las columnas existan
                for col in nueva_fila_df.columns:
                    if col not in self.df.columns:
                        self.df[col] = None
    
                self.df = pd.concat([self.df, nueva_fila_df], ignore_index=True)
                self.df = self.df.drop_duplicates(subset=['Prefijo', 'Número'], keep='last')
                self.df['Fecha'] = pd.to_datetime(self.df['Fecha'], errors='coerce')
                self.df = self.df.sort_values('Fecha', ascending=False)
    
            # ✅ **LÓGICA CORREGIDA: Solo insertar en TNS si NO existe**
            if not existe_en_tns and os.getenv('TNS_INSERT', 'False').lower() == 'true':
                self.log(f"🚀 Insertando en TNS: {prefijo_makos}-{numero_makos}")
                if self._insertar_en_tns_y_validar(new_row):
                    self.log(f"✅ Inserción TNS exitosa: {prefijo_makos}-{numero_makos}")
                else:
                    self.log(f"❌ Error en inserción TNS: {prefijo_makos}-{numero_makos}")
            elif existe_en_tns:
                self.log(f"ℹ️ Factura ya existe en TNS, no se inserta: {prefijo_makos}-{numero_makos}")
    
            # ✅ NO guardar después de cada factura (se guarda al final del scraping)
            # Esto evita guardar SQLite 14 veces innecesariamente
            return True
    
        except Exception as e:
            self.log(f"❌ Error procesando factura nueva: {str(e)}")
            import traceback
            self.log(f"🔍 Detalle del error: {traceback.format_exc()}")
            return False
        
        finally:
            with self.processing_lock:
                if factura_id in self.facturas_procesando:
                    self.facturas_procesando.remove(factura_id)
    
    def _obtener_facturas_por_rango(self):
        """Obtiene las facturas del Excel dentro del rango de fechas seleccionado"""
        try:
            if not hasattr(self, 'df') or self.df.empty:
                return []

            # ✅ VALIDAR CHECKBOX "USAR FECHAS"
            if not self.usar_fechas_var.get():
                self.log("🔓 Validando TODAS las facturas (sin filtro de fechas)")
                return self.df.to_dict('records')

            # ✅ VALIDAR CHECKBOX "DÍA ACTUAL"
            if self.dia_actual_var.get():
                # Usar día actual para ambas fechas
                fecha_actual = datetime.now().strftime('%Y-%m-%d')
                fecha_desde = pd.to_datetime(fecha_actual)
                fecha_hasta = pd.to_datetime(fecha_actual)
                self.log(f"📅 Validando facturas del día actual: {fecha_actual}")
            else:
                # Usar rango personalizado
                fecha_desde_str = self.fecha_desde_var.get()
                fecha_hasta_str = self.fecha_hasta_var.get()
                
                try:
                    fecha_desde = pd.to_datetime(fecha_desde_str)
                    fecha_hasta = pd.to_datetime(fecha_hasta_str)
                except Exception as e:
                    self.log(f"⚠️ Error en formato de fechas: {e} - Usando rango por defecto")
                    fecha_hasta = pd.to_datetime(datetime.now())
                    fecha_desde = fecha_hasta - timedelta(days=7)

            # Asegurar que la columna Fecha sea datetime
            df_filtrado = self.df.copy()
            df_filtrado['Fecha'] = pd.to_datetime(df_filtrado['Fecha'], errors='coerce')

            # Filtrar por rango de fechas
            mask = (df_filtrado['Fecha'] >= fecha_desde) & (df_filtrado['Fecha'] <= fecha_hasta)
            facturas_filtradas = df_filtrado[mask].to_dict('records')

            self.log(f"📅 Validando {len(facturas_filtradas)} facturas del rango {fecha_desde.strftime('%Y-%m-%d')} a {fecha_hasta.strftime('%Y-%m-%d')}")
            return facturas_filtradas

        except Exception as e:
            self.log(f"⚠️ Error obteniendo facturas por rango: {str(e)}")
            return []

    def _obtener_todas_las_facturas_excel(self):
            """Obtiene todas las facturas del Excel para validación"""
            try:
                if not hasattr(self, 'df') or self.df.empty:
                    return []
                return self.df.to_dict('records')
            except Exception as e:
                self.log(f"⚠️ Error obteniendo facturas del Excel: {str(e)}")
                return []
            
    def _validar_lote_facturas_tns(self, facturas_excel):
        """Valida un lote de facturas contra TNS en lotes de 50 - SOLUCIÓN MÍNIMA"""
        if not facturas_excel:
            self.log("ℹ️ No hay facturas para validar")
            return
    
        self.log(f"🔍 Validando {len(facturas_excel)} facturas con TNS (en lotes de 1000)...")
    
        # ✅ DIVIDIR EN LOTES DE 1000 (Firebird límite: 1500)
        lote_tamano = 1000
        lotes = [facturas_excel[i:i + lote_tamano] for i in range(0, len(facturas_excel), lote_tamano)]
    
        total_procesadas = 0
    
        for num_lote, lote in enumerate(lotes, 1):
            self.log(f"📦 Procesando lote {num_lote}/{len(lotes)} ({len(lote)} facturas)")
    
            try:
                # 1. Preparar lista de valores OBSERV para consulta
                observ_list = []
                facturas_por_observ = {}
    
                for factura in lote:
                    prefijo = factura['Prefijo']
                    numero = factura['Número']
                    observ = f"{prefijo}{numero}"
                    observ_list.append(observ)
                    facturas_por_observ[observ] = factura
    
                # 2. CONSULTA MASIVA POR LOTE (máximo 1000)
                if not self.firebird._verificar_conexion():
                    self.log("❌ No hay conexión a Firebird para validación masiva")
                    continue
                
                cur = self.firebird.conexion.cursor()
    
                # Construir consulta con múltiples parámetros (máximo 1000)
                placeholders = ','.join(['?' for _ in observ_list])
                query = f"""
                    SELECT OBSERV, KARDEXID, TOTAL, NETOBASE, NETOIVA, VRICONSUMO, CODPREFIJO, NUMERO 
                    FROM KARDEX 
                    WHERE OBSERV IN ({placeholders})
                """
    
                cur.execute(query, observ_list)
                resultados_tns = cur.fetchall()
                cur.close()
    
                # 3. Procesar resultados del lote actual
                facturas_validadas_en_lote = 0
    
                # Primero procesar las que SÍ existen en TNS
                for row in resultados_tns:
                    observ, kardexid, total_tns, netobase_tns, netoiva_tns, vriconsumo_tns, prefijo_tns, numero_tns = row
    
                    if observ in facturas_por_observ:
                        factura_data = facturas_por_observ[observ]
                        self._procesar_validacion_individual(
                            factura_data, 
                            True,  # existe_en_tns
                            kardexid,
                            float(total_tns) if total_tns else 0.0,
                            float(netobase_tns) if netobase_tns else 0.0,
                            float(netoiva_tns) if netoiva_tns else 0.0,
                            float(vriconsumo_tns) if vriconsumo_tns else 0.0,
                            prefijo_tns,
                            numero_tns
                        )
                        facturas_validadas_en_lote += 1
                        del facturas_por_observ[observ]  # Remover de pendientes
    
                # 4. Procesar las que NO existen en TNS en este lote
                for observ, factura_data in facturas_por_observ.items():
                    self._procesar_validacion_individual(
                        factura_data,
                        False,  # existe_en_tns
                        None, 0.0, 0.0, 0.0, 0.0, '', ''
                    )
                    facturas_validadas_en_lote += 1
    
                total_procesadas += facturas_validadas_en_lote
                self.log(f"✅ Lote {num_lote} completado: {facturas_validadas_en_lote} facturas validadas")
    
            except Exception as e:
                self.log(f"❌ Error en lote {num_lote}: {str(e)}")
                # Fallback: validación individual para este lote
                self.log(f"🔄 Reintentando lote {num_lote} con validación individual...")
                for factura in lote:
                    try:
                        self._validar_factura_con_tns(factura)
                    except:
                        pass  # Ignorar errores individuales
                total_procesadas += len(lote)
    
        self.log(f"✅ Validación masiva completada: {total_procesadas} facturas procesadas en {len(lotes)} lotes")

    def _procesar_validacion_individual(self, factura_data, existe_en_tns, kardexid, total_tns, netobase_tns, netoiva_tns, vriconsumo_tns, prefijo_tns, numero_tns):
        """Procesa los resultados de validación para una factura individual"""
        try:
            prefijo_makos = factura_data['Prefijo']
            numero_makos = factura_data['Número']
            total_makos = float(factura_data.get('Total', 0))
            impuestos_makos = float(factura_data.get('ImpuestosMakos', 0))
            observ_value = f"{prefijo_makos}{numero_makos}"

            # Buscar la factura en el DataFrame
            mask = (self.df['Prefijo'] == prefijo_makos) & (self.df['Número'] == numero_makos)
            if not mask.any():
                return

            if existe_en_tns:
                # ✅ CALCULAR DIFERENCIA EXACTA
                impuestos_tns = netoiva_tns + vriconsumo_tns
                diferencia_impuestos = impuestos_makos - impuestos_tns

                # Validaciones
                totales_coinciden = abs(total_makos - total_tns) < 0.01

                if totales_coinciden:
                    impuestos_coinciden = abs(diferencia_impuestos) <= 1.00
                else:
                    impuestos_coinciden = abs(diferencia_impuestos) < 0.01

                estado = 'TNS_VALIDADO' if totales_coinciden else 'TNS_ERROR_TOTAL'

                # Actualizar DataFrame con TODOS los campos
                self.df.loc[mask, 'TNS'] = 'SÍ'
                self.df.loc[mask, 'Estado'] = estado
                self.df.loc[mask, 'KARDEXID'] = kardexid
                self.df.loc[mask, 'TotalTNS'] = total_tns
                self.df.loc[mask, 'Validacion'] = 'OK' if totales_coinciden else 'ERROR'
                self.df.loc[mask, 'NetoBaseTNS'] = netobase_tns
                self.df.loc[mask, 'IvaTNS'] = netoiva_tns
                self.df.loc[mask, 'ImpConsumoTNS'] = vriconsumo_tns
                self.df.loc[mask, 'ValidacionImpuestos'] = 'OK' if impuestos_coinciden else 'ERROR'
                self.df.loc[mask, 'DiferenciaImpuestos'] = diferencia_impuestos
                self.df.loc[mask, 'PrefijoTNS'] = prefijo_tns
                self.df.loc[mask, 'NumeroTNS'] = numero_tns

                if totales_coinciden:
                    if impuestos_coinciden:
                        self.log(f"   ✅ {observ_value}: Validación COMPLETA OK")
                    else:
                        self.log(f"   ⚠️ {observ_value}: Total OK, impuestos difieren ${diferencia_impuestos:,.2f}")
                else:
                    self.log(f"   ❌ {observ_value}: Total no coincide (Makos: ${total_makos:,.2f} vs TNS: ${total_tns:,.2f})")

            else:
                # Factura NO EXISTE en TNS
                self.df.loc[mask, 'TNS'] = 'NO'
                self.df.loc[mask, 'Estado'] = 'PENDIENTE_TNS'
                self.df.loc[mask, 'KARDEXID'] = ''
                self.df.loc[mask, 'TotalTNS'] = 0
                self.df.loc[mask, 'Validacion'] = 'PENDIENTE'
                self.df.loc[mask, 'NetoBaseTNS'] = 0
                self.df.loc[mask, 'IvaTNS'] = 0
                self.df.loc[mask, 'ImpConsumoTNS'] = 0
                self.df.loc[mask, 'ValidacionImpuestos'] = 'PENDIENTE'
                self.df.loc[mask, 'DiferenciaImpuestos'] = 0
                self.df.loc[mask, 'PrefijoTNS'] = ''
                self.df.loc[mask, 'NumeroTNS'] = ''

                self.log(f"   ❌ {observ_value}: No existe en TNS")

                # Intentar inserción si está configurado
                if os.getenv('TNS_INSERT', 'False').lower() == 'true':
                    self.log(f"   🚀 Intentando inserción en TNS: {observ_value}")
                    # La inserción sigue siendo individual como antes
                    threading.Thread(target=self._insertar_en_tns_y_validar, args=(factura_data,), daemon=True).start()

            # ✅ NO guardar aquí - se guarda al final del scraping completo

        except Exception as e:
            self.log(f"❌ Error procesando validación individual: {str(e)}")
    
    def _insertar_en_tns_y_validar(self, factura_data):
        """Inserta en TNS y luego valida los datos CON VALIDACIÓN DE IMPUESTOS"""
        try:
            prefijo_makos = factura_data['Prefijo']
            numero_makos = factura_data['Número']
            total_makos = float(factura_data.get('Total', 0))
            impuestos_makos = float(factura_data.get('ImpuestosMakos', 0))

            self.log(f"🔥 Insertando en TNS: {prefijo_makos}-{numero_makos}")

            time.sleep(1)
            success = self.firebird.insertar_factura(factura_data)

            if success:
                time.sleep(2)
                existe_en_tns, kardexid, total_tns, netobase_tns, netoiva_tns, vriconsumo_tns, prefijo_tns, numero_tns = self.firebird.factura_existe(prefijo_makos, numero_makos)

                if existe_en_tns:
                    # ✅ APLICAR LA MISMA LÓGICA FLEXIBLE
                    totales_coinciden = abs(total_makos - total_tns) < 0.01

                    impuestos_tns = netoiva_tns + vriconsumo_tns
                    diferencia_impuestos = abs(impuestos_makos - impuestos_tns)

                    if totales_coinciden:
                        impuestos_coinciden = diferencia_impuestos <= 1.00
                    else:
                        impuestos_coinciden = diferencia_impuestos < 0.01

                    # Actualizar Excel
                    mask = (self.df['Prefijo'] == prefijo_makos) & (self.df['Número'] == numero_makos)
                    if mask.any():
                        self.df.loc[mask, 'TNS'] = 'SÍ'
                        self.df.loc[mask, 'Estado'] = 'TNS_VALIDADO' if totales_coinciden else 'TNS_ERROR_TOTAL'
                        self.df.loc[mask, 'KARDEXID'] = kardexid
                        self.df.loc[mask, 'TotalTNS'] = total_tns
                        self.df.loc[mask, 'Validacion'] = 'OK' if totales_coinciden else 'ERROR'
                        self.df.loc[mask, 'NetoBaseTNS'] = netobase_tns
                        self.df.loc[mask, 'IvaTNS'] = netoiva_tns
                        self.df.loc[mask, 'ImpConsumoTNS'] = vriconsumo_tns
                        self.df.loc[mask, 'ValidacionImpuestos'] = 'OK' if impuestos_coinciden else 'ERROR'
                        self.df.loc[mask, 'DiferenciaImpuestos'] = diferencia_impuestos  
                        # ✅ NO guardar aquí - se guarda al final del scraping completo

                        if totales_coinciden and impuestos_coinciden:
                            self.log(f"✅ Inserción COMPLETA OK: {prefijo_makos}-{numero_makos}")
                        elif totales_coinciden and not impuestos_coinciden:
                            self.log(f"⚠️ Inserción PARCIAL: Total OK, impuestos con diferencia de ${diferencia_impuestos:.2f}")
                        else:
                            self.log(f"❌ Inserción con ERROR: Total no coincide")    
                else:
                    self.log(f"❌ Inserción fallida - No se encontró en TNS: {prefijo_makos}-{numero_makos}")

                return True
            else:
                self.log(f"❌ Error insertando en TNS: {prefijo_makos}-{numero_makos}")
                return False

        except Exception as e:
            self.log(f"❌ Error crítico en inserción TNS: {str(e)}")
            return False

    def _validar_factura_con_tns(self, factura_data):
        """Valida una factura comparando datos de Makos con TNS - CON DIFERENCIA EXACTA"""
        try:
            prefijo_makos = factura_data['Prefijo']
            numero_makos = factura_data['Número']
            total_makos = float(factura_data.get('Total', 0))
            impuestos_makos = float(factura_data.get('ImpuestosMakos', 0))
            observ_value = f"{prefijo_makos}{numero_makos}"

            self.log(f"🔍 Validando factura: {observ_value}")

            # Verificar en TNS
            existe_en_tns, kardexid, total_tns, netobase_tns, netoiva_tns, vriconsumo_tns, prefijo_tns, numero_tns = self.firebird.factura_existe(prefijo_makos, numero_makos)

            mask = (self.df['Prefijo'] == prefijo_makos) & (self.df['Número'] == numero_makos)
            if not mask.any():
                return

            if existe_en_tns:
                # ✅ CALCULAR DIFERENCIA EXACTA
                impuestos_tns = netoiva_tns + vriconsumo_tns
                diferencia_impuestos = impuestos_makos - impuestos_tns  # ✅ DIFERENCIA EXACTA (puede ser positiva o negativa)

                # Validaciones
                totales_coinciden = abs(total_makos - total_tns) < 0.01

                if totales_coinciden:
                    impuestos_coinciden = abs(diferencia_impuestos) <= 1.00
                else:
                    impuestos_coinciden = abs(diferencia_impuestos) < 0.01

                estado = 'TNS_VALIDADO' if totales_coinciden else 'TNS_ERROR_TOTAL'

                # Actualizar DataFrame con TODOS los campos
                self.df.loc[mask, 'TNS'] = 'SÍ'
                self.df.loc[mask, 'Estado'] = estado
                self.df.loc[mask, 'KARDEXID'] = kardexid
                self.df.loc[mask, 'TotalTNS'] = total_tns
                self.df.loc[mask, 'Validacion'] = 'OK' if totales_coinciden else 'ERROR'
                self.df.loc[mask, 'NetoBaseTNS'] = netobase_tns
                self.df.loc[mask, 'IvaTNS'] = netoiva_tns
                self.df.loc[mask, 'ImpConsumoTNS'] = vriconsumo_tns
                self.df.loc[mask, 'ValidacionImpuestos'] = 'OK' if impuestos_coinciden else 'ERROR'
                self.df.loc[mask, 'DiferenciaImpuestos'] = diferencia_impuestos  # ✅ GUARDAR DIFERENCIA
                self.df.loc[mask, 'PrefijoTNS'] = prefijo_tns
                self.df.loc[mask, 'NumeroTNS'] = numero_tns

                if totales_coinciden:
                    if impuestos_coinciden:
                        self.log(f"✅ Validación COMPLETA OK: {observ_value}")
                        self.log(f"   💰 Total: Makos ${total_makos:,.2f} = TNS ${total_tns:,.2f}")
                        self.log(f"   📊 Impuestos: Makos ${impuestos_makos:,.2f} = TNS ${impuestos_tns:,.2f}")
                    else:
                        self.log(f"⚠️ Validación PARCIAL: Total OK pero impuestos con diferencia de ${diferencia_impuestos:,.2f}")
                        self.log(f"   💰 Total: Makos ${total_makos:,.2f} = TNS ${total_tns:,.2f} ✅")
                        self.log(f"   📊 Impuestos: Makos ${impuestos_makos:,.2f} ≠ TNS ${impuestos_tns:,.2f} (diferencia: ${diferencia_impuestos:,.2f})")
                else:
                    self.log(f"❌ ERROR Validación: {observ_value}")
                    self.log(f"   💰 Total: Makos ${total_makos:,.2f} ≠ TNS ${total_tns:,.2f}")
                    self.log(f"   📊 Impuestos: Makos ${impuestos_makos:,.2f} vs TNS ${impuestos_tns:,.2f} (diferencia: ${diferencia_impuestos:,.2f})")

            else:
                # Factura NO EXISTE en TNS
                self.df.loc[mask, 'TNS'] = 'NO'
                self.df.loc[mask, 'Estado'] = 'PENDIENTE_TNS'
                self.df.loc[mask, 'KARDEXID'] = ''
                self.df.loc[mask, 'TotalTNS'] = 0
                self.df.loc[mask, 'Validacion'] = 'PENDIENTE'
                self.df.loc[mask, 'NetoBaseTNS'] = 0
                self.df.loc[mask, 'IvaTNS'] = 0
                self.df.loc[mask, 'ImpConsumoTNS'] = 0
                self.df.loc[mask, 'ValidacionImpuestos'] = 'PENDIENTE'
                self.df.loc[mask, 'DiferenciaImpuestos'] = 0  # ✅ Diferencia 0 cuando no existe en TNS

                self.log(f"❌ No existe en TNS: {observ_value}")

                if os.getenv('TNS_INSERT', 'False').lower() == 'true':
                    self.log(f"🚀 Intentando inserción en TNS: {observ_value}")
                    threading.Thread(target=self._insertar_en_tns_y_validar, args=(factura_data,), daemon=True).start()

            # ✅ NO guardar aquí - se guarda al final del scraping completo

        except Exception as e:
            self.log(f"❌ Error validando factura: {str(e)}")

    def _llamar_endpoint_list_invoices(self, fecha_desde=None, fecha_hasta=None):
        """Llama al endpoint ListInvoices con un rango de fechas específico"""
        try:
            headers = {
                "Authorization": self.HEADERS["Authorization"],
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            if fecha_desde and fecha_hasta:
                payload = {
                    "FECHA1": fecha_desde,
                    "FECHA2": fecha_hasta,
                    "PARAM1": "0"
                }
            else:
                payload = {
                    "PARAM1": "0"
                }

            response = requests.post(
                "https://pos.appmakos.com:3333/ReportSales/ListInvoices",
                headers=headers,
                json=payload,
                timeout=20
            )

            if response.status_code == 200:
                # ✅ GARANTIZAR PROCESAMIENTO DE TODOS LOS BLOQUES
                # El endpoint siempre envía todos los bloques concatenados: [{...}][{...}][{...}]
                # Necesitamos procesar TODOS los bloques sin perder ninguno
                texto_respuesta = response.text.strip()
                datos = []
                total_bloques_procesados = 0
                
                # ✅ PASO 1: Verificar si hay múltiples arrays concatenados por "]["
                if '][' in texto_respuesta:
                    self.log(f"📦 Detectados múltiples bloques concatenados (separador: '][')")
                    self.log(f"📝 Longitud respuesta: {len(texto_respuesta)} caracteres")
                    
                    # Dividir por "][" que separa los bloques
                    partes = texto_respuesta.split('][')
                    self.log(f"🔍 Encontrados {len(partes)} bloques potenciales")
                    
                    for i, parte in enumerate(partes, 1):
                        try:
                            # Agregar corchetes si faltan
                            parte_limpia = parte.strip()
                            if not parte_limpia.startswith('['):
                                parte_limpia = '[' + parte_limpia
                            if not parte_limpia.endswith(']'):
                                parte_limpia = parte_limpia + ']'
                            
                            array_parseado = json.loads(parte_limpia)
                            if isinstance(array_parseado, list):
                                num_facturas_bloque = len(array_parseado)
                                datos.extend(array_parseado)
                                total_bloques_procesados += 1
                                self.log(f"  ✅ Bloque {i}/{len(partes)}: {num_facturas_bloque} facturas procesadas")
                            else:
                                self.log(f"  ⚠️ Bloque {i}: No es un array válido")
                        except json.JSONDecodeError as e:
                            self.log(f"  ⚠️ Error parseando bloque {i}: {str(e)}")
                            continue
                        except Exception as e:
                            self.log(f"  ⚠️ Error procesando bloque {i}: {str(e)}")
                            continue
                    
                    self.log(f"📊 Total bloques procesados: {total_bloques_procesados}/{len(partes)}")
                    
                else:
                    # ✅ PASO 2: Intentar parsear como JSON normal (un solo array o array de arrays)
                    try:
                        datos_parseados = json.loads(texto_respuesta)
                        
                        # Verificar si es array de arrays [[{...}], [{...}]]
                        if isinstance(datos_parseados, list) and len(datos_parseados) > 0 and isinstance(datos_parseados[0], list):
                            self.log(f"📦 Detectado array de arrays: {len(datos_parseados)} bloques anidados")
                            for i, subarray in enumerate(datos_parseados, 1):
                                if isinstance(subarray, list):
                                    num_facturas_bloque = len(subarray)
                                    datos.extend(subarray)
                                    total_bloques_procesados += 1
                                    self.log(f"  ✅ Bloque {i}/{len(datos_parseados)}: {num_facturas_bloque} facturas procesadas")
                            self.log(f"📊 Total bloques procesados: {total_bloques_procesados}/{len(datos_parseados)}")
                        elif isinstance(datos_parseados, list):
                            # Es un solo array normal (un solo bloque)
                            datos = datos_parseados
                            total_bloques_procesados = 1
                            self.log(f"📦 Array único (1 bloque): {len(datos)} facturas")
                        else:
                            self.log(f"⚠️ Respuesta no es un array válido")
                            datos = []
                            total_bloques_procesados = 0
                    except json.JSONDecodeError:
                        self.log(f"⚠️ No se pudo parsear como JSON válido")
                        datos = []
                        total_bloques_procesados = 0
                    except Exception as e:
                        self.log(f"⚠️ Error parseando respuesta: {str(e)}")
                        datos = []
                        total_bloques_procesados = 0
                
                # ✅ GARANTÍA: Verificar que se procesaron datos
                if not datos:
                    self.log(f"⚠️ ADVERTENCIA: No se procesaron facturas de la respuesta")
                else:
                    self.log(f"✅ Total facturas procesadas de todos los bloques: {len(datos)}")
                
                # ✅ GARANTÍA: Los datos ya están aplanados (todos los bloques combinados)
                # No necesitamos procesar arrays anidados porque ya los procesamos arriba
                
                facturas = []
                
                # ✅ PROCESAR CADA FACTURA DE TODOS LOS BLOQUES
                for item in datos:
                    if not isinstance(item, dict):
                        continue
                        
                    digitosprefijo = int(os.getenv('DIGITOS_PREFIJO', '2'))
                    prefix = item['invoice'][:digitosprefijo]
                    number = item['invoice'][digitosprefijo:]
                    
                    if not prefix.isalpha():
                        self.log(f"⚠️ Prefijo inválido en '{item['invoice']}', se reasigna a 'UC'")
                        prefix = 'UC'
                        number = item['invoice']
                    
                    iddocument = int(os.getenv(prefix, "0"))
                    
                    facturas.append({
                        'iddocument': iddocument,
                        'prefix': prefix,
                        'number': number,
                        'datedoc': item['datedoc'],
                        'hourdoc': item.get('hourdoc', '00:00'),
                        'idcontact': 0,
                        'enabled': item['enabled'],
                        'alias': item['alias'],
                        'total': item['total'],
                        'tip': item['tip'],
                        'subtotal': item['subtotal'],
                        'impuestos': item['impuestos'],
                        'idstatus': 7 if item['enabled'] == 'Activo' else 0
                    })

                # ✅ GARANTÍA FINAL: Verificar que todas las facturas se procesaron
                if len(facturas) != len(datos):
                    self.log(f"⚠️ ADVERTENCIA: Se procesaron {len(facturas)} facturas de {len(datos)} datos recibidos")
                    self.log(f"   Esto puede indicar que algunas facturas no tenían el formato correcto")
                else:
                    self.log(f"✅ GARANTÍA: Todas las {len(facturas)} facturas fueron procesadas correctamente")
                
                self.log(f"📊 Resumen: {total_bloques_procesados} bloque(s) → {len(facturas)} facturas procesadas")
                return facturas

            elif response.status_code == 401:
                self.log("🔒 Sesión expirada, intentando reautenticar...")
                if self.smart_login():
                    return self._llamar_endpoint_list_invoices(fecha_desde, fecha_hasta)
                raise Exception("No se pudo reautenticar")

            else:
                raise Exception(f"Error API (HTTP {response.status_code})")

        except Exception as e:
            raise Exception(f"Error llamando endpoint: {str(e)}")

    def _obtener_facturas_api(self):
        """Obtiene facturas desde el endpoint API con validación de checkboxes y división automática de fechas"""
        try:
            # ✅ VERIFICAR QUE HEADERS EXISTA
            if not hasattr(self, 'HEADERS') or not self.HEADERS:
                self.log("⚠️ HEADERS no inicializado, intentando login...")
                if not self.smart_login():
                    raise Exception("No se pudo inicializar HEADERS")

            # ✅ VALIDAR CHECKBOX "USAR FECHAS"
            if self.usar_fechas_var.get():
                # ✅ VALIDAR CHECKBOX "DÍA ACTUAL"
                if self.dia_actual_var.get():
                    # Usar día actual para ambas fechas
                    fecha_hasta_actual = datetime.now().strftime('%Y-%m-%d')
                    fecha_desde_api = fecha_hasta_actual
                    
                    # ✅ CONSULTA DE SEGURIDAD: También consultar el día anterior en dos casos:
                    # 1. Después de las 20:00 (8 PM) hasta 23:59
                    # 2. Entre 00:00 y 00:30 (medianoche hasta media hora)
                    # Esto evita perder facturas que pueden tener delay en aparecer en el endpoint
                    # o que el endpoint tenga límites y no retorne todas las facturas del día actual
                    # El problema reportado: a las 10:30 PM se cortó, pero al día siguiente sí funcionó
                    rangos_fechas = [(fecha_desde_api, fecha_hasta_actual)]  # Día actual
                    
                    # Obtener hora y minuto actuales
                    ahora = datetime.now()
                    hora_actual = ahora.hour
                    minuto_actual = ahora.minute
                    
                    # Log de hora actual
                    self.log(f"📅 Consulta con día actual: {fecha_desde_api} (Hora: {hora_actual:02d}:{minuto_actual:02d})")
                    
                    # Caso 1: Después de las 20:00 (8 PM) hasta 23:59
                    # Caso 2: Entre 00:00 y 00:30 (medianoche hasta media hora)
                    consultar_dia_anterior_seguridad = False
                    motivo = ""
                    
                    if hora_actual >= 20:  # Después de las 8 PM
                        consultar_dia_anterior_seguridad = True
                        motivo = f"después de 20:00 (hora actual: {hora_actual:02d}:{minuto_actual:02d})"
                    elif hora_actual == 0 and minuto_actual <= 30:  # Entre 00:00 y 00:30
                        consultar_dia_anterior_seguridad = True
                        motivo = f"entre 00:00 y 00:30 (hora actual: {hora_actual:02d}:{minuto_actual:02d})"
                    
                    if consultar_dia_anterior_seguridad:
                        fecha_ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                        rangos_fechas.append((fecha_ayer, fecha_ayer))
                        self.log(f"🛡️ Consulta de seguridad ({motivo}): También consultando día anterior ({fecha_ayer})")
                        self.log(f"   Esto evita perder facturas con delay en el endpoint o límites del mismo")
                else:
                    # Usar rango de fechas personalizado
                    fecha_hasta_actual = self.fecha_hasta_var.get()
                    fecha_desde_gui = self.fecha_desde_var.get()
                    
                    # Calcular fecha desde restando días históricos
                    fecha_desde_dt = datetime.strptime(fecha_desde_gui, '%Y-%m-%d')
                    fecha_desde_api = (fecha_desde_dt - timedelta(days=self.DIAS_HISTORICO)).strftime('%Y-%m-%d')
                    self.log(f"📅 Consulta con rango personalizado: {fecha_desde_api} a {fecha_hasta_actual}")
                    
                    # ✅ DIVIDIR EL RANGO EN DÍAS INDIVIDUALES para evitar límites del endpoint
                    fecha_desde_dt = datetime.strptime(fecha_desde_api, '%Y-%m-%d')
                    fecha_hasta_dt = datetime.strptime(fecha_hasta_actual, '%Y-%m-%d')
                    rangos_fechas = []
                    fecha_actual = fecha_desde_dt
                    while fecha_actual <= fecha_hasta_dt:
                        fecha_str = fecha_actual.strftime('%Y-%m-%d')
                        rangos_fechas.append((fecha_str, fecha_str))
                        fecha_actual += timedelta(days=1)
                    
                    self.log(f"📊 Dividido en {len(rangos_fechas)} día(s) para evitar límites del endpoint")
            else:
                # ❌ NO USAR FECHAS - Consulta sin filtro de fechas
                self.log("🔓 Consulta SIN filtro de fechas")
                rangos_fechas = [(None, None)]

            # ✅ HACER MÚLTIPLES LLAMADAS Y COMBINAR RESULTADOS
            todas_las_facturas = []
            facturas_unicas = set()  # Para evitar duplicados
            consultar_dia_anterior = False  # Flag para consulta de seguridad
            
            for idx, (fecha_desde, fecha_hasta) in enumerate(rangos_fechas, 1):
                try:
                    if fecha_desde and fecha_hasta:
                        self.log(f"📡 Llamada {idx}/{len(rangos_fechas)}: {fecha_desde} a {fecha_hasta}")
                    else:
                        self.log(f"📡 Llamada {idx}/{len(rangos_fechas)}: Sin filtro de fechas")
                    
                    facturas = self._llamar_endpoint_list_invoices(fecha_desde, fecha_hasta)
                    
                    # ✅ Filtrar duplicados usando (prefix, number) como clave única
                    for factura in facturas:
                        clave_unica = (factura['prefix'], factura['number'])
                        if clave_unica not in facturas_unicas:
                            facturas_unicas.add(clave_unica)
                            todas_las_facturas.append(factura)
                    
                    self.log(f"✅ Recibidas {len(facturas)} facturas en llamada {idx} (total acumulado: {len(todas_las_facturas)})")
                    
                    # ✅ DETECCIÓN DE AGRUPAMIENTO EN BLOQUES DE 100
                    # El endpoint agrupa facturas en bloques de 100: [0-99], [100-199], [200-299], etc.
                    # Si retorna exactamente 100, 200, 300, etc., podría haber más facturas en el siguiente bloque
                    # También detecta números cercanos a múltiplos de 100 (98-102, 198-202, etc.)
                    num_facturas = len(facturas)
                    es_dia_actual = fecha_desde == fecha_hasta and fecha_desde == datetime.now().strftime('%Y-%m-%d')
                    
                    # Detectar si es múltiplo exacto de 100 (100, 200, 300, 400, 500, etc.)
                    es_multiplo_100 = num_facturas > 0 and num_facturas % 100 == 0
                    
                    # Detectar si está cerca de un múltiplo de 100 (margen de ±2)
                    # Ejemplos: 98, 99, 100, 101, 102 → cerca de 100
                    #           198, 199, 200, 201, 202 → cerca de 200
                    es_cercano_multiplo_100 = False
                    if num_facturas >= 98:  # Solo verificar si hay suficientes facturas
                        multiplo_inferior = (num_facturas // 100) * 100
                        multiplo_superior = multiplo_inferior + 100
                        distancia_inferior = abs(num_facturas - multiplo_inferior)
                        distancia_superior = abs(num_facturas - multiplo_superior)
                        es_cercano_multiplo_100 = distancia_inferior <= 2 or distancia_superior <= 2
                    
                    if es_dia_actual and (es_multiplo_100 or es_cercano_multiplo_100):
                        if es_multiplo_100:
                            self.log(f"⚠️ Posible bloque completo detectado: {num_facturas} facturas (múltiplo de 100)")
                            self.log(f"   El endpoint agrupa en bloques de 100, podría haber más facturas en el siguiente bloque")
                        else:
                            self.log(f"⚠️ Posible bloque completo detectado: {num_facturas} facturas (cercano a múltiplo de 100)")
                            self.log(f"   El endpoint agrupa en bloques de 100, podría haber más facturas")
                        consultar_dia_anterior = True
                    
                except Exception as e:
                    self.log(f"⚠️ Error en llamada {idx}: {str(e)}")
                    continue
            
            # ✅ CONSULTA DE SEGURIDAD: Si detectamos un posible límite, consultar día anterior
            if consultar_dia_anterior:
                fecha_ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                # Verificar si ya consultamos el día anterior
                if (fecha_ayer, fecha_ayer) not in rangos_fechas:
                    self.log(f"🛡️ Consultando día anterior ({fecha_ayer}) como seguridad para evitar pérdida de facturas...")
                    try:
                        facturas_ayer = self._llamar_endpoint_list_invoices(fecha_ayer, fecha_ayer)
                        for factura in facturas_ayer:
                            clave_unica = (factura['prefix'], factura['number'])
                            if clave_unica not in facturas_unicas:
                                facturas_unicas.add(clave_unica)
                                todas_las_facturas.append(factura)
                        self.log(f"✅ Día anterior: {len(facturas_ayer)} facturas adicionales (total: {len(todas_las_facturas)})")
                    except Exception as e:
                        self.log(f"⚠️ Error consultando día anterior: {str(e)}")

            self.log(f"✅ Total final: {len(todas_las_facturas)} facturas únicas desde la API")
            return todas_las_facturas

        except Exception as e:
            raise Exception(f"Error obteniendo facturas: {str(e)}")

    def _factura_existe(self, prefijo, numero):
        """Verifica si la factura ya existe en el DataFrame (EXCEL)"""
        try:
            if not hasattr(self, 'df') or self.df.empty:
                return False

            mask = (self.df['Prefijo'].astype(str) == str(prefijo)) & \
                   (self.df['Número'].astype(str) == str(numero))

            return mask.any()
        except Exception as e:
            self.log(f"⚠️ Error verificando en Excel: {str(e)}")
            return False

    def _ya_insertada_en_tns(self, prefijo, numero):
        """Verifica si la factura ya está en TNS"""
        if not hasattr(self, 'df') or self.df.empty:
            return False
        tns_value = f"{prefijo}{numero}"
        # Verificación en base de datos (simplificada)
        return False

    def _get_detalle_factura_api(self, factura):
        """Obtiene detalles completos de una factura usando los endpoints API con reintento de login"""
        detalles = {
            'header': {},
            'items': [],
            'payments': []
        }
        print(f"[DEBUG] factura object original: {factura}")

        max_intentos = 2  # Máximo 2 intentos (1 normal + 1 con reintento de login)
        intento = 0

        while intento < max_intentos:
            intento += 1
            try:
                self.log(f"🔍 Obteniendo detalles de Makos (intento {intento}): {factura['prefix']}-{factura['number']}")

                # 1. OBTENER CABECERA
                header_url = f"https://pos.appmakos.com:3333/Invoices/header?iddocument={factura['iddocument']}&prefix={factura['prefix']}&numberdoc={factura['number']}"
                header_response = requests.get(
                    header_url, headers=self.HEADERS, timeout=15)

                # ✅ VERIFICAR SI LA RESPUESTA ES JSON VÁLIDO
                try:
                    header_data = header_response.json()
                    if header_response.status_code == 200:
                        detalles['header'] = header_data
                        print(f"[DEBUG] Respuesta de cabecera: {header_data}")
                    else:
                        raise Exception(f"Error HTTP {header_response.status_code} en cabecera")

                except json.JSONDecodeError:
                    # ❌ NO ES JSON - PROBABLEMENTE SESIÓN EXPIRADA
                    self.log("🔒 Sesión expirada detectada en cabecera (respuesta no JSON)")
                    if intento < max_intentos:
                        self.log("🔄 Reintentando login...")
                        if self.smart_login():
                            continue  # Reintentar con nueva sesión
                        else:
                            raise Exception("No se pudo reautenticar")
                    else:
                        raise Exception("Sesión expirada y no se pudo reautenticar")

                # 2. OBTENER ARTÍCULOS
                items_url = f"https://pos.appmakos.com:3333/Invoices/details?iddocument={factura['iddocument']}&numberdoc={factura['number']}"
                items_response = requests.get(
                    items_url, headers=self.HEADERS, timeout=15)

                # ✅ VERIFICAR SI LA RESPUESTA ES JSON VÁLIDO
                try:
                    items_data = items_response.json()
                    if items_response.status_code == 200:
                        detalles['items'] = items_data
                        print(f"[DEBUG] Respuesta de artículos: {items_data}")
                    else:
                        raise Exception(f"Error HTTP {items_response.status_code} en artículos")

                except json.JSONDecodeError:
                    self.log("🔒 Sesión expirada detectada en artículos (respuesta no JSON)")
                    if intento < max_intentos:
                        self.log("🔄 Reintentando login...")
                        if self.smart_login():
                            continue  # Reintentar con nueva sesión
                        else:
                            raise Exception("No se pudo reautenticar")
                    else:
                        raise Exception("Sesión expirada y no se pudo reautenticar")

                totalfactura = float(factura.get('total', 0))
                valortotalitems = 0

                # 3. PROCESAR ARTÍCULOS (cálculos existentes)
                for item in detalles['items']:
                    item['vunitario'] = (item.get('subtotal', 0) /
                                         item.get('quantity', 1))
                    item['vunitariotax'] = item.get(
                        'taxes', 0) / item.get('quantity', 1)
                    item['vunitariototal'] = item.get(
                        'vunitario', 0) + item.get('vunitariotax', 0)
                    item['vtotal'] = item.get('subtotal', 0) + item.get('taxes', 0)
                    valortotalitems += item['vtotal']

                # 4. OBTENER PAGOS (¡ESTE ES EL PASO CRÍTICO!)
                payments_url = f"https://pos.appmakos.com:3333/Invoices/payments?iddocument={factura['iddocument']}&numberdoc={factura['number']}"
                print(f"[DEBUG] URL de pagos: {payments_url}")

                try:
                    payments_response = requests.get(
                        payments_url, headers=self.HEADERS, timeout=15)
                    payments_response.raise_for_status()

                    # ✅ VERIFICAR SI LA RESPUESTA ES JSON VÁLIDO
                    try:
                        payments_data = payments_response.json()
                        print(f"[DEBUG] Respuesta de pagos: {payments_data}")
                    except json.JSONDecodeError:
                        self.log("🔒 Sesión expirada detectada en pagos (respuesta no JSON)")
                        if intento < max_intentos:
                            self.log("🔄 Reintentando login...")
                            if self.smart_login():
                                continue  # Reintentar con nueva sesión
                            else:
                                raise Exception("No se pudo reautenticar")
                        else:
                            raise Exception("Sesión expirada y no se pudo reautenticar")

                    payment_types = {
                        "0": {"code": "EF", "name": "Efectivo"},
                        "1": {"code": "TC", "name": "Tarjeta Crédito"},
                        "2": {"code": "TD", "name": "Tarjeta Débito"},
                        "3": {"code": "RP", "name": "Rappi (Cuentas por Cobrar)"},
                        "4": {"code": "TR", "name": "Transferencia"},
                        "6": {"code": "TG", "name": "Transferencia Guerreros (Cheques)"},
                    }

                    # 5. CALCULAR PAYMENTTOTAL CON DATOS REALES
                    paymenttotal = sum(float(p.get('valuepay', 0))
                                       for p in payments_data)

                    detalles['payments'] = payments_data 

                    # 6. APLICAR REGLAS DE INVERSIÓN (AHORA CON DATOS REALES) si nit es 222 y pago es EF
                    # 1. Verificar regla de NIT 1090465454
                    if detalles['header'].get('nit', '') == '1090465454':
                        if paymenttotal == 0:
                            detalles['header']['prefix'] = detalles['header'].get('prefix', '')[
                                                                                  ::-1]

                    # 2. Verificar regla de NIT 222222222222
                    elif detalles['header'].get('nit', '') == '222222222222':
                        # Verificar si hay pago en efectivo
                        tiene_efectivo = any(
                            p['payname'] == 'Efectivo' for p in detalles['payments'])

                        if paymenttotal == 0 or tiene_efectivo:
                            detalles['header']['prefix'] = detalles['header'].get('prefix', '')[
                                                                                  ::-1]

                    # 3. Verificar regla para otros NITs
                    else:
                        if paymenttotal == 0:
                            detalles['header']['prefix'] = detalles['header'].get('prefix', '')[
                                                                                  ::-1]

                    # 7. PROCESAR CÓDIGOS DE PAGO (USANDO PREFIJO CORRECTO)
                    for payment in payments_data:
                        payment_info = payment_types.get(
                            payment['idpay'], {"code": "OTRO", "name": "Otro método"})
                        payment['payname'] = payment_info['name']

                        # Usar el prefijo que ya pudo haber sido invertido
                        payment['paycode'] = payment_info['code'] + \
                            detalles['header'].get('prefix', '')

                    # 8. AGREGAR REGALO/CORTESÍA SI ES NECESARIO
                    #if (float(totalfactura) - float(valortotalitems) > 0):
                    #    payments_data.append({
                    #        "valuepay": float(totalfactura) - float(valortotalitems),
                    #        "payname": "REGALO/CORTESÍA",
                    #        "paycode": "GF" + detalles['header'].get('prefix', ''),
                    #        "idpay": "9"
                    #    })

                    # 9. FINALMENTE GUARDAR LOS PAGOS
                    detalles['payments'] = payments_data

                except requests.exceptions.RequestException as e:
                    self.log(f"Error al obtener pagos: {str(e)}")
                    detalles['payments'] = []

                # 10. OBTENER UBICACIÓN
                ubicacion = ""
                if 'idtable' in factura and factura['idtable']:
                    ubicacion = self.obtener_ubicacion_mesa(factura['idtable'])
                elif 'idtable' in detalles['header'] and detalles['header']['idtable']:
                    ubicacion = self.obtener_ubicacion_mesa(
                        detalles['header']['idtable'])

                # 11. COMBINAR TODOS LOS DATOS
                resultado = {**factura, **detalles['header']}
                resultado['items'] = detalles['items']
                resultado['payments'] = detalles['payments']
                resultado['address'] = ubicacion

                self.log(f"✅ Detalles obtenidos correctamente en intento {intento}: {factura['prefix']}-{factura['number']}")
                return resultado

            except Exception as e:
                self.log(f"❌ Error en intento {intento} para {factura['prefix']}-{factura['number']}: {str(e)}")

                # Si es el último intento y aún falla, devolver estructura básica
                if intento >= max_intentos:
                    self.log(f"🚫 No se pudieron obtener detalles después de {max_intentos} intentos para {factura['prefix']}-{factura['number']}")
                    return {
                        **factura, 
                        'items': [], 
                        'payments': [], 
                        'address': f"MESA {factura.get('idtable', '')}",
                        'header': {}
                    }

        # Fallback final si todo falla
        return {
            **factura, 
            'items': [], 
            'payments': [], 
            'address': f"MESA {factura.get('idtable', '')}",
            'header': {}
        }
    
    def obtener_ubicacion_mesa(self, id_mesa: int) -> str:
        """Obtiene el nombre de la ubicación (mesa) desde la API"""
        try:
            url = f"https://pos.appmakos.com:3333/SalesArea/Location/{id_mesa}"
            headers = {
                "Authorization": f"Bearer {self.API_TOKEN}",
                "Accept": "application/json"
            }

            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Default si no hay nombre
                return data.get("name", f"MESA {id_mesa}")
            else:
                self.log(
                    f"⚠️ Error al obtener ubicación (HTTP {response.status_code}): {response.text}")
                return f"MESA {id_mesa}"

        except Exception as e:
            self.log(f"❌ Error al obtener ubicación: {str(e)}")
            return f"MESA {id_mesa}"

    
    def smart_login(self):
        """Autenticación inteligente con token persistente"""
        token_file = os.path.join(BASE_DIR, "api_token.txt")

        # Intentar con token existente
        if os.path.exists(token_file):
            try:
                with open(token_file, "r") as f:
                    token_data = json.load(f)
                self.API_TOKEN = token_data["token"]
                self.HEADERS = {"Authorization": f"Bearer {self.API_TOKEN}"}

                if self._verify_token_validity():
                    self.log("✅ Sesión recuperada desde token")
                    return True
                else:
                    os.remove(token_file)
            except:
                pass

        # Login normal con nuevo payload
        try:
            # Obtener fecha actual en formato requerido
            current_time = datetime.now()
            formatted_date = current_time.strftime("%d/%m/%Y, %H:%M:%S GMT-5")

            payload = {
                "username": self.CREDENTIALS['username'],
                "password": self.CREDENTIALS['password'],
                "ip": self.CREDENTIALS.get('ip', '143.105.99.221'),
                "device": self.CREDENTIALS.get('device', 'desktop'),
                "datelogin": formatted_date
            }

            response = requests.post(
                "https://pos.appmakos.com:3333/Login/guerreros",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )

            if response.status_code == 200:
                auth_data = response.json()
                self.API_TOKEN = auth_data["token"]
                self.HEADERS = {"Authorization": f"Bearer {self.API_TOKEN}"}

                # Guardar token
                with open(token_file, "w") as f:
                    json.dump({"token": self.API_TOKEN, "timestamp": datetime.now().isoformat()}, f)

                self.log("✅ Autenticación exitosa")
                return True
            else:
                self.log(f"❌ Error de autenticación: {response.status_code}")
                return False

        except Exception as e:
            self.log(f"❌ Error en login: {str(e)}")
            return False

    def _verify_token_validity(self):
        """Verifica si el token es válido"""
        try:
            response = requests.get(
                "https://pos.appmakos.com:3333/Invoices/?filter=",
                headers={"Authorization": f"Bearer {self.API_TOKEN}"},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def hacer_logout(self):
        """Cierra sesión en el servidor y elimina el token local"""
        token_file = os.path.join(BASE_DIR, "api_token.txt")
        
        try:
            # Cerrar sesión en el servidor
            if hasattr(self, 'API_TOKEN') and self.API_TOKEN:
                try:
                    requests.get("https://pos.appmakos.com:3333/Logoutm3",
                               headers={"Authorization": f"Bearer {self.API_TOKEN}"},
                               timeout=5)
                    self.log("🔓 Logout exitoso en el servidor")
                except Exception as e:
                    self.log(f"⚠️ Error en logout del servidor: {str(e)}")
            
            # Eliminar token local
            if os.path.exists(token_file):
                try:
                    os.remove(token_file)
                    self.log("🗑️ Token local eliminado")
                except Exception as e:
                    self.log(f"⚠️ Error eliminando token local: {str(e)}")
            
            # Limpiar variables
            self.API_TOKEN = None
            self.HEADERS = {}
            
            return True
        except Exception as e:
            self.log(f"⚠️ Error en logout: {str(e)}")
            return False
    
    def renovar_sesion(self):
        """Renueva la sesión haciendo logout y login para evitar caducidad del token"""
        try:
            self.log("🔄 Renovando sesión (logout + login) para evitar caducidad del token...")
            
            # 1. Hacer logout
            self.hacer_logout()
            
            # 2. Esperar 5 segundos antes de login (dar tiempo al servidor para cerrar sesión)
            time.sleep(5)
            
            # 3. Hacer login (esto actualizará el token en api_token.txt)
            if self.smart_login():
                self.log("✅ Sesión renovada exitosamente")
                return True
            else:
                self.log("❌ Error renovando sesión: no se pudo hacer login")
                return False
        except Exception as e:
            self.log(f"❌ Error renovando sesión: {str(e)}")
            return False
          
    def guardar_excel(self):
        """
        Guarda el DataFrame en SQLite (reemplaza Excel)
        MANTIENE EXACTAMENTE la misma interfaz - NO modifica lógica de inserción Firebird
        """
        try:
            if not hasattr(self, 'df') or self.df.empty:
                self.log("⚠️ No hay datos para guardar")
                return False
            
            # ✅ Verificar que db esté inicializado
            if not hasattr(self, 'db') or self.db is None:
                self.db = MakosDatabase(log_callback=self.log)

            # ✅ ASEGURAR QUE EXISTAN TODAS LAS COLUMNAS (igual que antes)
            for columna in self.columnas_requeridas:
                if columna not in self.df.columns:
                    if any(x in columna for x in ['Total', 'Subtotal', 'Impuestos', 'Propina', 'Base', 'IVA', 'Consumo', 'Diferencia']):
                        self.df[columna] = 0.0
                    else:
                        self.df[columna] = ''

            # ✅ GUARDAR EN SQLite (misma interfaz, solo cambia el backend)
            return self.db.guardar_facturas(self.df)

        except Exception as e:
            self.log(f"❌ Error al guardar: {str(e)}")
            import traceback
            self.log(f"🔍 Detalle del error: {traceback.format_exc()}")
            return False

    def cargar_facturas(self):
        """
        Carga las facturas desde SQLite (reemplaza Excel)
        MANTIENE EXACTAMENTE la misma interfaz - self.df sigue siendo DataFrame
        """
        try:
            # ✅ Verificar que db esté inicializado
            if not hasattr(self, 'db') or self.db is None:
                self.db = MakosDatabase(log_callback=self.log)
            
            # ✅ CARGAR DESDE SQLite (misma interfaz, solo cambia el backend)
            self.df = self.db.cargar_facturas(self.columnas_requeridas)
            
            # ✅ MANTENER MISMAS VALIDACIONES Y PROCESAMIENTO (igual que Excel)
            if not self.df.empty:
                # Limpiar y preparar datos (igual que antes)
                self.df = self.df.drop_duplicates(subset=['Prefijo', 'Número'], keep='last')
                
                # Asegurar que Fecha sea datetime (igual que antes)
                if 'Fecha' in self.df.columns:
                    self.df['Fecha'] = pd.to_datetime(self.df['Fecha'], errors='coerce')
                    self.df = self.df.sort_values('Fecha', ascending=False)
                else:
                    self.log("⚠️ Advertencia: No se encontró columna 'Fecha'")
                    self.df['Fecha'] = datetime.now()
                    self.df = self.df.sort_index(ascending=False)
                
                self.log(f"📊 Facturas cargadas - {len(self.df)} registros únicos")
                self.actualizar_estadisticas()
                self.actualizar_treeview()
                return True
            else:
                # Crear estructura vacía (igual que antes)
                self.df = pd.DataFrame(columns=self.columnas_requeridas)
                self.log("🆕 Base de datos vacía - Se creará con estructura nueva")
                return False

        except Exception as e:
            self.log(f"❌ Error al cargar facturas: {str(e)}")
            import traceback
            self.log(f"🔍 Detalle del error: {traceback.format_exc()}")
            # Crear DataFrame vacío como fallback (igual que antes)
            self.df = pd.DataFrame(columns=self.columnas_requeridas)
            return False

    def actualizar_estadisticas(self):
        """Actualiza las estadísticas en la interfaz"""
        if hasattr(self, 'df') and not self.df.empty:
            total = len(self.df)
            hoy = len(self.df[self.df['Fecha'].dt.date == datetime.now().date()])
            insertadas = len(self.df[self.df['TNS'] != ''])
            
            self.total_facturas_var.set(str(total))
            self.facturas_hoy_var.set(str(hoy))
            self.facturas_insertadas_var.set(str(insertadas))
            self.estado_sistema_var.set("Conectado ✅")

    def actualizar_treeview(self):
        """Actualiza el treeview con las facturas - CON ORDEN CORRECTO"""
        if not hasattr(self, 'tree'):
            return

        # Limpiar treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Insertar datos en el ORDEN CORRECTO
        for _, row in self.df.iterrows():
            diferencia = row.get('DiferenciaImpuestos', 0)
            diferencia_str = f"${diferencia:,.2f}" if pd.notna(diferencia) and diferencia != 0 else ""

            self.tree.insert("", "end", values=(
                # ✅ ORDEN EXACTO COMO DEFINIMOS EN columns
                row.get('Fecha', ''),
                row.get('Prefijo', ''),
                row.get('Número', ''),
                row.get('Cliente', ''),
                f"${float(row.get('Total', 0)):,.0f}",
                f"${float(row.get('SubtotalMakos', 0)):,.0f}",
                f"${float(row.get('ImpuestosMakos', 0)):,.0f}",
                f"${float(row.get('PropinaMakos', 0)):,.0f}",
                row.get('Estado', ''),
                "✓" if row.get('TNS', '') == 'SÍ' else "✗",
                row.get('Validacion', ''),
                row.get('ValidacionImpuestos', ''),
                diferencia_str,
                row.get('KARDEXID', ''),
                row.get('PrefijoTNS', ''),
                row.get('NumeroTNS', ''),
                f"${float(row.get('TotalTNS', 0)):,.0f}" if pd.notna(row.get('TotalTNS')) and row.get('TotalTNS', 0) != 0 else '',
                f"${float(row.get('NetoBaseTNS', 0)):,.0f}" if pd.notna(row.get('NetoBaseTNS')) and row.get('NetoBaseTNS', 0) != 0 else '',
                f"${float(row.get('IvaTNS', 0)):,.0f}" if pd.notna(row.get('IvaTNS')) and row.get('IvaTNS', 0) != 0 else '',
                f"${float(row.get('ImpConsumoTNS', 0)):,.0f}" if pd.notna(row.get('ImpConsumoTNS')) and row.get('ImpConsumoTNS', 0) != 0 else ''
            ))

    def actualizar_interfaz_despues_scraping(self):
        """Actualiza la interfaz después del scraping"""
        try:
            self.cargar_facturas()
            self.actualizar_treeview()
            self.actualizar_estadisticas()
            self.log("✅ Interfaz actualizada correctamente")
        except Exception as e:
            self.log(f"⚠️ Error al actualizar interfaz: {str(e)}")

    def log(self, mensaje):
        """Muestra logs en la interfaz y archivo - VERSIÓN MÁS ROBUSTA"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        mensaje_completo = f"[{timestamp}] {mensaje}"

        # ✅ ESCRIBIR A ARCHIVO DE LOG
        if self.log_file:
            try:
                self.log_file.write(mensaje_completo + "\n")
                self.log_file.flush()  # Forzar escritura inmediata
            except Exception as e:
                print(f"[ERROR] No se pudo escribir en log: {e}")

        # Determinar tag basado en el contenido
        if "✅" in mensaje or "ÉXITO" in mensaje:
            tag = "success"
        elif "❌" in mensaje or "ERROR" in mensaje:
            tag = "error"
        elif "⚠️" in mensaje or "ADVERTENCIA" in mensaje:
            tag = "warning"
        else:
            tag = "info"

        print(mensaje_completo)

        def actualizar_gui():
            try:
                # Verificar que los componentes aún existen
                if (hasattr(self, 'log_textbox') and 
                    self.log_textbox is not None and 
                    self.root.winfo_exists()):

                    self.log_textbox.config(state=tk.NORMAL)
                    self.log_textbox.insert(tk.END, mensaje_completo + "\n", tag)
                    self.log_textbox.see(tk.END)
                    self.log_textbox.config(state=tk.DISABLED)

            except Exception as e:
                print(f"Error updating GUI (ignored): {str(e)}")

        try:
            # Verificar si estamos en el hilo principal
            if threading.current_thread() == threading.main_thread():
                actualizar_gui()
            else:
                # Programar en el hilo principal de manera segura
                if hasattr(self, 'root') and self.root.winfo_exists():
                    self.root.after(0, actualizar_gui)
        except Exception as e:
            print(f"Error scheduling log update (ignored): {str(e)}")

    def on_close(self):
        """Maneja el cierre seguro de la aplicación"""
        # ✅ CERRAR ARCHIVO DE LOG
        if self.log_file:
            try:
                self.log_file.write(f"\n{'='*80}\n")
                self.log_file.write(f"APLICACION CERRADA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.log_file.write(f"{'='*80}\n")
                self.log_file.close()
                print(f"[LOG] Archivo de log cerrado correctamente")
            except Exception as e:
                print(f"[ERROR] Error cerrando archivo de log: {e}")
        
        token_file = os.path.join(BASE_DIR, "api_token.txt")
        
        try:
            # Cerrar sesión en el servidor
            if hasattr(self, 'API_TOKEN') and self.API_TOKEN:
                try:
                    requests.get("https://pos.appmakos.com:3333/Logoutm3",
                               headers={"Authorization": f"Bearer {self.API_TOKEN}"},
                               timeout=5)
                except:
                    pass

            # Eliminar token
            if os.path.exists(token_file):
                try:
                    os.remove(token_file)
                except:
                    pass

            # Cerrar conexiones
            if hasattr(self, 'firebird') and hasattr(self.firebird, 'conexion'):
                try:
                    self.firebird.conexion.close()
                except:
                    pass

            # Guardar datos
            if hasattr(self, 'df') and not self.df.empty:
                try:
                    self.guardar_excel()
                except:
                    pass

        except Exception as e:
            print(f"Error en cierre: {str(e)}")
        finally:
            self.root.destroy()


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = AplicacionScraping(root)
        root.mainloop()
    except Exception as e:
        # ✅ MANEJO DE ERRORES para que no se cierre solo
        import traceback
        error_msg = f"❌ ERROR CRÍTICO:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        
        # Si hay ventana de tkinter, mostrar error
        try:
            import tkinter.messagebox as mb
            mb.showerror("Error Crítico", error_msg)
        except:
            pass
        
        # Si está compilado como .exe, mantener consola abierta
        if getattr(sys, 'frozen', False):
            input("\nPresiona ENTER para cerrar...")
        
        sys.exit(1)