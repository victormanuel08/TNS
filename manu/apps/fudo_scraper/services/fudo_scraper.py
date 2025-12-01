import os
import json
import requests
import time
import firebirdsql
import platform
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from django.conf import settings
from apps.sistema_analitico.models import EmpresaServidor, Servidor

# Importar fcntl para locks (Unix) o msvcrt (Windows)
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
    try:
        import msvcrt
        HAS_MSVCRT = True
    except ImportError:
        HAS_MSVCRT = False

class FudoScraperService:
    """Servicio para hacer scraping de FUDO y insertar en Firebird"""

    def __init__(self, session_id: int, empresa_servidor: EmpresaServidor, usuario: str, password: str):
        self.session_id = session_id
        self.empresa_servidor = empresa_servidor
        self.usuario = usuario
        self.password = password
        self.base_url = os.getenv('FUDO_API_URL', 'https://api.fu.do')
        self.auth_url = os.getenv('FUDO_AUTH_URL', 'https://auth.fu.do/authenticate')
        self.cluster_id = os.getenv('FUDO_CLUSTER_ID', '2')
        self.token_info = {
            'token': None,
            'expires_at': None
        }
        self.auth_data = {
            "login": usuario,
            "password": password
        }
        self.firebird_conn = None
        self.cache = {
            'product_categories': {'data': None, 'last_updated': None},
            'payment_types': {'data': None, 'last_updated': None},
            'guests': {'data': None, 'last_updated': None},
            'rooms': {'data': None, 'last_updated': None},
            'sale_states': {'data': None, 'last_updated': None},
            'products': {'data': None, 'last_updated': None},
            'users': {'data': None, 'last_updated': None}
        }

    def obtener_token(self):
        """Obtiene y almacena el token de autenticación con su fecha de expiración"""
        if self.token_info['token'] and self.token_info['expires_at']:
            now = datetime.now(timezone.utc)
            if now < self.token_info['expires_at']:
                return self.token_info['token']

        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            self.auth_url, headers=headers, data=json.dumps(self.auth_data), timeout=30)

        if response.status_code == 200:
            self.token_info['token'] = response.json()["token"]
            self.token_info['expires_at'] = datetime.now(timezone.utc) + timedelta(hours=1)
            return self.token_info['token']
        raise Exception(
            f"Error en autenticación: {response.status_code} - {response.text}")

    def obtener_datos(self, endpoint, params=None, item_id=None):
        """Función genérica para obtener datos con caché inteligente"""
        cache_key = endpoint.replace('/', '_')
        if params:
            cache_key += "_" + "_".join(f"{k}={v}" for k, v in params.items())

        # Verificar caché
        if not os.getenv('FORCE_CACHE', '0') == '1':
            today = datetime.now(timezone.utc).date()
            if (self.cache.get(cache_key, {}).get('data') is not None and
                    self.cache[cache_key]['last_updated'] == today):
                if item_id is None:
                    return self.cache[cache_key]['data']
                return next((item for item in self.cache[cache_key]['data'] if str(item['id']) == str(item_id)), None)

        if not self.token_info['token']:
            self.obtener_token()

        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.token_info["token"]}',
            'fudo-cluster-id': self.cluster_id,
            'Accept': 'application/json'
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            datos = response.json()

            # Convertir a lista de diccionarios si es objeto
            if isinstance(datos, dict):
                datos = [{"id": int(k) if k.isdigit() else k, **v}
                         for k, v in datos.items()]

            # Actualizar caché
            today = datetime.now(timezone.utc).date()
            if endpoint == 'products' and params and params.get('a') == -1:
                self.cache['products'] = {'data': datos, 'last_updated': today}
            else:
                self.cache[cache_key] = {'data': datos, 'last_updated': today}

            if item_id is not None:
                return next((item for item in datos if str(item['id']) == str(item_id)), None)

            return datos
        raise Exception(
            f"Error al obtener {endpoint}: {response.status_code} - {response.text}")

    def obtener_ventas(self, fecha_inicio, fecha_fin, dc=0, estado=3):
        """Obtiene ventas detalladas con paginación automática"""
        fecha_inicio, fecha_fin = self._formatear_fechas(fecha_inicio, fecha_fin)

        headers = {
            'Authorization': f'Bearer {self.token_info["token"]}',
            'fudo-cluster-id': self.cluster_id,
            'Accept': 'application/json'
        }

        all_ventas = {}
        page = 1
        base_url = f"{self.base_url}/sales?dc={dc}&ss={estado}&t1={fecha_inicio}&t2={fecha_fin}"

        while True:
            try:
                url = base_url if page == 1 else f"{base_url}&page={page}"
                response = requests.get(url, headers=headers, timeout=30)

                if response.status_code != 200:
                    break

                ventas_pagina = response.json()

                if not ventas_pagina:
                    break

                all_ventas.update(ventas_pagina)
                page += 1
                time.sleep(0.1)

            except requests.exceptions.RequestException:
                break
            except Exception:
                break

        # Ordenar por ID numérico
        ids_ordenados = sorted(all_ventas.keys(), key=int)
        ventas_ordenadas = {id_ordenado: all_ventas[id_ordenado] for id_ordenado in ids_ordenados}

        return ventas_ordenadas

    def _formatear_fechas(self, fecha_inicio, fecha_fin):
        """Formatea fechas para la API"""
        if fecha_inicio and 'T' in str(fecha_inicio):
            return fecha_inicio, fecha_fin

        if hasattr(fecha_inicio, 'strftime'):
            fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
        else:
            fecha_inicio_str = str(fecha_inicio)

        if hasattr(fecha_fin, 'strftime'):
            fecha_fin = fecha_fin + timedelta(days=1)
            fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
        else:
            fecha_fin_str = str(fecha_fin)

        fecha_inicio = f"{fecha_inicio_str}T05:01:00.000Z"
        fecha_fin = f"{fecha_fin_str}T04:59:00.000Z"

        return fecha_inicio, fecha_fin

    def _conectar_firebird(self):
        """Conecta a Firebird usando la configuración de la empresa"""
        if self.firebird_conn:
            return self.firebird_conn

        servidor = self.empresa_servidor.servidor
        
        # Construir ruta completa de la base de datos
        ruta_base = self.empresa_servidor.ruta_base
        if not ruta_base:
            raise Exception(f"No hay ruta_base configurada para la empresa {self.empresa_servidor.nombre}")

        try:
            self.firebird_conn = firebirdsql.connect(
                host=servidor.host,
                database=ruta_base,
                user=servidor.usuario,
                password=servidor.password,
                charset=os.getenv('FIREBIRD_CHARSET', 'ISO8859_1')
            )
            return self.firebird_conn
        except Exception as e:
            raise Exception(f"Error conectando a Firebird: {str(e)}")

    def _factura_existe(self, cur, fudo_original_id: str) -> bool:
        """Verifica si una factura ya existe en Firebird"""
        try:
            query = "SELECT 1 FROM KARDEX WHERE OBSERV = ?"
            cur.execute(query, (str(fudo_original_id),))
            return cur.fetchone() is not None
        except Exception:
            return False

    def _insertar_factura_firebird(self, factura: dict) -> bool:
        """Inserta una factura completa en Firebird"""
        try:
            conn = self._conectar_firebird()
            cur = conn.cursor()

            if self._factura_existe(cur, factura['fudo_original_id']):
                cur.close()
                return True  # Ya existe, no insertar

            prefijo = os.getenv('PREFIX', 'FE')
            fecha = datetime.strptime(factura['fecha'], '%Y-%m-%d').date()
            detalles = factura['detalles']
            forma_de_pago = detalles.get('payments', [])
            AREAFV = 3

            nit = detalles.get('nit', '222222222222')
            if not forma_de_pago:
                cur.close()
                return True

            onenotEF = False
            for pago in forma_de_pago:
                if pago.get('paycode') == 'EF' and os.getenv('REVERSE_PREFIX', 'False') == 'True' and nit == '222222222222':
                    prefijo = pago.get('paycode')
                    AREAFV = 4
                if pago.get('paycode') != 'EF':
                    onenotEF = True

            if onenotEF:
                prefijo = os.getenv('PREFIX', 'FE')

            # Obtener próximo número
            numero = self._obtener_proximo_numero(cur, prefijo)

            # Insertar cabecera
            self._insertar_cabecera(cur, prefijo, numero, fecha, detalles)

            # Insertar items
            self._insertar_items(cur, prefijo, numero, detalles['items'])

            # Insertar pagos
            self._insertar_pagos(cur, prefijo, numero, detalles['payments'])

            # Actualizar totales
            self._actualizar_totales(cur, prefijo, numero)

            # Actualizar campos adicionales
            self._actualizar_campos_adicionales(cur, prefijo, numero, factura, AREAFV)

            conn.commit()
            cur.close()
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            raise Exception(f"Error insertando factura: {str(e)}")

    def _obtener_proximo_numero(self, cur, prefijo: str) -> str:
        """
        Obtiene el próximo número de factura con lock para evitar race conditions.
        Usa lock de archivo para evitar que dos procesos Celery tomen el mismo consecutivo.
        """
        # Lock de archivo (funciona entre procesos de Celery)
        lock_file_path = None
        if platform.system() == 'Windows':
            lock_file_path = os.path.join(tempfile.gettempdir(), f"fudo_consecutivo_{prefijo}.lock")
        else:
            lock_file_path = f"/tmp/fudo_consecutivo_{prefijo}.lock"
        
        # Lock de archivo (funciona entre procesos)
        lock_file = None
        try:
            # Crear lock de archivo
            lock_file = open(lock_file_path, 'w')
            if HAS_FCNTL:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            elif HAS_MSVCRT:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            
            # Ahora obtener el consecutivo de forma segura
            time.sleep(0.1)  # Pequeña espera para asegurar que el lock está activo
            
            cur.execute(
                "SELECT CONSECUTIVO FROM CONSECUTIVO WHERE CODCOMP = 'FV' AND CODPREFIJO = ?",
                (prefijo,)
            )
            resultado = cur.fetchone()
            
            if not resultado:
                # Si no existe, crear el registro
                cur.execute("""
                    INSERT INTO CONSECUTIVO (CODCOMP, CODPREFIJO, CONSECUTIVO)
                    VALUES ('FV', ?, 0)
                """, (prefijo,))
                self.firebird_conn.commit()
                numero_actual = 0
            else:
                numero_actual = int(resultado[0])
            
            # Calcular próximo número
            proximo_numero = numero_actual + 1
            
            # Actualizar inmediatamente
            cur.execute("""
                UPDATE CONSECUTIVO 
                SET CONSECUTIVO = ?
                WHERE CODCOMP = 'FV' AND CODPREFIJO = ?
            """, (proximo_numero, prefijo))
            self.firebird_conn.commit()
            
            return str(proximo_numero)
            
        except Exception as e:
            # Si falla el lock, intentar sin lock (menos seguro pero funcional)
            print(f"⚠️ Advertencia: No se pudo obtener lock para consecutivo {prefijo}: {str(e)}")
            time.sleep(0.3)  # Esperar un poco más para evitar conflictos
            cur.execute(
                "SELECT CONSECUTIVO FROM CONSECUTIVO WHERE CODCOMP = 'FV' AND CODPREFIJO = ?",
                (prefijo,)
            )
            resultado = cur.fetchone()
            numero_actual = int(resultado[0]) if resultado else 0
            proximo_numero = numero_actual + 1
            
            cur.execute("""
                UPDATE CONSECUTIVO 
                SET CONSECUTIVO = ?
                WHERE CODCOMP = 'FV' AND CODPREFIJO = ?
            """, (proximo_numero, prefijo))
            self.firebird_conn.commit()
            
            return str(proximo_numero)
            
        finally:
            # Liberar lock
            if lock_file:
                try:
                    if HAS_FCNTL:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    elif HAS_MSVCRT:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    lock_file.close()
                    # Eliminar archivo de lock
                    try:
                        if os.path.exists(lock_file_path):
                            os.remove(lock_file_path)
                    except:
                        pass
                except:
                    pass

    def _insertar_cabecera(self, cur, prefijo: str, numero: str, fecha, detalles: dict):
        """Inserta la cabecera de la factura"""
        nit = detalles.get('nit', '222222222222')
        params = (
            'FV',            # CODCOMP
            prefijo,         # CODPREFIJO
            numero,          # NUMERO
            fecha,           # FECHA
            fecha.strftime("%m"),  # MES
            'MU',           # TIPO (MU = Multiples)
            '0',            # CODVEN
            'ADMIN',        # USUARIO
            prefijo,        # SUCURSAL
            nit,            # NIT
            None,           # OBSERV (opcional)
            '2'             # ESTADO (2 = Activo)
        )
        cur.execute("SELECT * FROM TNS_INS_FACTURAVTA(?,?,?,?,?,?,?,?,?,?,?,?)", params)
        if not cur.fetchone():
            raise Exception("Error al insertar cabecera")

    def _insertar_items(self, cur, prefijo: str, numero: str, items: list):
        """Inserta los items de la factura"""
        for item in items:
            codebar = item.get('fudo_product_id', '')
            if not self._existe_material(cur, codebar) and codebar != 'TIP':
                self._crear_material(cur, item)

            if self._existe_material(cur, codebar) or codebar == 'TIP':
                params = (
                    numero, str(codebar), '0',
                    str(int(item.get('quantity', 1))),
                    str(item.get('price', 0)),
                    prefijo, 'FV'
                )
                time.sleep(0.5)
                if not item.get('canceled', False):
                    cur.execute("SELECT * FROM TNS_INS_DETALLEFACTVTA(?,?,?,?,?,?,?)", params)
                    cur.fetchone()

    def _insertar_pagos(self, cur, prefijo: str, numero: str, payments: list):
        """Inserta los métodos de pago"""
        for pago in payments:
            params = (
                str(numero), 'FV', prefijo,
                pago['paycode'], '1005038638-2',
                float(pago['valuepay'])
            )
            cur.execute("EXECUTE PROCEDURE TNS_INS_DEKARDEXFP(?,?,?,?,?,?)", params)

    def _actualizar_totales(self, cur, prefijo: str, numero: str):
        """Actualiza los totales de la factura"""
        cur.execute("SELECT * FROM TNS_ACTTOTALFACT('FV', ?, ?)", (prefijo, numero))
        cur.fetchall()

    def _actualizar_campos_adicionales(self, cur, prefijo: str, numero: str, factura: dict, areafv: int):
        """Actualiza campos adicionales"""
        cur.execute("""
            UPDATE CONSECUTIVO SET CONSECUTIVO = ?
            WHERE CODCOMP = 'FV' AND CODPREFIJO = ?
        """, (numero, prefijo))
        time.sleep(0.5)

        hora_24 = datetime.now().strftime('%H:%M')
        cur.execute("""
            UPDATE KARDEX
            SET HORAASEN = ?, HORA = ?, OBSERV = ?, CENID = ?, AREADID = ?, CUFE = ?, ESTADODIAN = ?
            WHERE CODCOMP = ? AND CODPREFIJO = ? AND NUMERO = ? 
        """, (
            hora_24, hora_24, factura['fudo_original_id'],
            factura['centro'], areafv, factura.get('cufe', ''),
            factura.get('estado_dian', ''), 'FV', prefijo, numero
        ))

    def _existe_material(self, cur, codigo: str) -> bool:
        """Verifica si un material existe"""
        cur.execute("SELECT 1 FROM MATERIAL WHERE CODIGO = ?", (codigo,))
        return cur.fetchone() is not None

    def _crear_material(self, cur, item: dict):
        """Crea un nuevo material"""
        grupo = item.get('categoria', {})
        grupofinal = self._existe_grupo_material(cur, grupo)
        codebar = str(item.get('fudo_product_id', '00'))
        nombre = item.get('name', 'Artículo sin nombre')
        precio = float(item.get('price', 0))

        cur.execute("SELECT * FROM TNS_INS_MATERIAL(?,?,?,?,?,?,?)",
                   (codebar, nombre, grupofinal, '00', '01', '0', str(precio)))
        cur.fetchone()

        cur.execute("SELECT MATID FROM MATERIAL WHERE CODIGO = ?", (codebar,))
        material = cur.fetchone()
        if material:
            material_id = material[0]
            cur.execute("""
                UPDATE MATERIALSUC 
                SET PORIMPCONS = 8, IMPCONS = 0 
                WHERE MATID = ? AND SUCID = '01'
            """, (material_id,))
            if cur.rowcount == 0:
                cur.execute("""
                    INSERT INTO MATERIALSUC (MATID, SUCID, PRECIO, PORIMPCONS, IMPCONS) 
                    VALUES (?, '01', ?, 8, 0)
                """, (material_id, precio))

    def _existe_grupo_material(self, cur, grupo: dict):
        """Verifica o crea grupo de material"""
        codgrupo = grupo.get('id', '99')
        nomgrupo = grupo.get('nombre', 'Pendientes')
        if len(str(codgrupo)) == 1:
            codgrupo = '0' + str(codgrupo)
        else:
            codgrupo = str(codgrupo)

        grupomat = "00.01." + codgrupo
        cur.execute("SELECT 1 FROM GRUPMAT WHERE CODIGO = ?", (grupomat,))
        if not cur.fetchone():
            cur.execute("INSERT INTO GRUPMAT (CODIGO, DESCRIP) VALUES (?, ?)", (grupomat, nomgrupo))
            self.firebird_conn.commit()
            time.sleep(0.3)
        return grupomat

    def _convertir_formato(self, factura_fudo: dict) -> dict:
        """Convierte el formato de FUDO al formato esperado por Firebird"""
        productos = self.cache['products']['data'] or []
        categorias = self.cache['product_categories']['data'] or []
        tipos_pago = self.cache['payment_types']['data'] or []
        huespedes = self.cache['guests']['data'] or []
        usuarios = self.cache['users']['data'] or []
        estados_venta = self.cache['sale_states']['data'] or []
        habitaciones = self.cache['rooms']['data'] or []

        CUFEFV = "No Fue Emitida Por Fudo A La DIAN"
        ESTADODIANFV = "NO EXITOSA"
        CENTROFV = 11
        AREAFV = 3

        if factura_fudo.get('invoicingStatus') == "INVOICED":
            cufe = (factura_fudo.get('lastReceipt', {})
                    .get('extraData', {})
                    .get('invoicer_response', {})
                    .get('meta', {})
                    .get('cufe'))
            if cufe:
                CUFEFV = cufe
                ESTADODIANFV = "EXITOSA"
                CENTROFV = 10

        prefijo = os.getenv('PREFIX', 'FE')
        numero = factura_fudo.get('numero', '')
        fecha_cerrada = factura_fudo.get('closedAt', datetime.now(UTC).isoformat())

        try:
            fecha = datetime.fromisoformat(fecha_cerrada.replace('Z', '+00:00')).strftime('%Y-%m-%d')
        except:
            fecha = datetime.now(UTC).strftime('%Y-%m-%d')

        info_huesped = {
            'nit': '222222222222',
            'nombre': None,
            'documento': None,
            'telefono': None,
            'direccion': None
        }

        if factura_fudo.get('guestId'):
            huesped = next((h for h in huespedes if h['id'] == factura_fudo['guestId']), None)
            if huesped:
                info_huesped.update({
                    'nit': huesped.get('document', '222222222222'),
                    'nombre': huesped.get('name'),
                    'documento': huesped.get('document'),
                    'telefono': huesped.get('phone'),
                    'direccion': ', '.join(huesped['address']) if huesped.get('address') else None
                })

        items_tns = []
        for prod in factura_fudo.get('additions', []):
            producto = next((p for p in productos if p['id'] == prod['productId']), None)

            categoria_info = {}
            if producto and 'productCategoryId' in producto:
                categoria_id = producto['productCategoryId']
                categoria = next((c for c in categorias if c['id'] == categoria_id), None)
                if categoria:
                    categoria_info = {
                        'id': categoria_id,
                        'nombre': categoria.get('name'),
                        'codigo': categoria.get('code')
                    }

            item_data = {
                'codebar': producto.get('code', f"ID{prod['productId']}") if producto else f"ID{prod['productId']}",
                'name': producto.get('name', f"Producto {prod['productId']}") if producto else f"Producto {prod['productId']}",
                'quantity': float(prod.get('count', 1)),
                'price': float(prod.get('price', 0))/float(prod.get('count', 1)),
                'subtotal': float(prod.get('price', 0)),
                'fudo_product_id': prod['productId'],
                'categoria': categoria_info,
                'comentario': prod.get('comment'),
                'cancelado': prod.get('canceled', False),
                'motivo_cancelacion': prod.get('cancellationComment') if prod.get('canceled') else None
            }

            if not item_data['cancelado']:
                items_tns.append(item_data)

        payments_tns = []
        for pago in factura_fudo.get('payments', []):
            tipo_pago = next((tp for tp in tipos_pago if tp['id'] == pago['paymentTypeId']), None)
            payment_data = {
                'paycode': self._paymentcode_traductor(pago['paymentTypeId']),
                'valuepay': float(pago.get('amount', 0)),
                'fudo_payment_type_id': pago['paymentTypeId'],
                'nombre_tipo_pago': tipo_pago.get('name') if tipo_pago else None,
                'codigo_tipo_pago': tipo_pago.get('code') if tipo_pago else None,
                'cancelado': pago.get('canceled', False),
                'comentario': pago.get('comment')
            }
            if not pago.get('canceled'):
                payments_tns.append(payment_data)

        for propina in factura_fudo.get('tips', []):
            item_data = {
                'codebar': 'TIP',
                'name': 'PROPINAS',
                'quantity': '1',
                'price': float(propina.get('amount', 0)),
                'subtotal': float(propina.get('amount', 0)),
                'fudo_product_id': 'TIP',
                'categoria': '00.00.01',
                'comentario': '',
                'cancelado': False,
                'motivo_cancelacion': ''
            }
            if not propina.get('canceled'):
                items_tns.append(item_data)

        factura_tns = {
            'fudo_original_id': factura_fudo.get('id'),
            'prefijo': prefijo,
            'numero': numero,
            'cufe': CUFEFV,
            'estado_dian': ESTADODIANFV,
            'centro': CENTROFV,
            'fecha': fecha,
            'fecha_cierre': factura_fudo.get('closedAt'),
            'comentario': factura_fudo.get('comment'),
            'detalles': {
                'cliente': info_huesped,
                'cufe': CUFEFV,
                'estado_dian': ESTADODIANFV,
                'centro': CENTROFV,
                'nit': info_huesped['nit'],
                'items': items_tns,
                'payments': payments_tns,
            },
        }

        return factura_tns

    def _paymentcode_traductor(self, id: str) -> str:
        """Traduce el código de pago"""
        id = str(id)
        traductor = {
            '1': 'EF', '2': 'C0', '3': 'TC', '4': 'TD',
            '5': 'TR', '6': 'CX', '7': 'RA'
        }
        return traductor.get(id, 'OT')

    def ejecutar_scraping(self, fecha_desde, fecha_hasta, callback=None):
        """Ejecuta el scraping completo"""
        from .models import FudoDocumentProcessed
        
        try:
            # 1. Autenticar
            self.obtener_token()

            # 2. Cargar datos necesarios
            endpoints = [
                ('product_categories', None),
                ('payment_types', None),
                ('guests', None),
                ('rooms', None),
                ('sale_states', None),
                ('products', {'a': -1}),
                ('users', None)
            ]

            for endpoint, params in endpoints:
                self.obtener_datos(endpoint, params=params)

            # 3. Obtener ventas
            ventas = self.obtener_ventas(fecha_desde, fecha_hasta, dc=0, estado=3)

            # 4. Procesar facturas
            total = len(ventas)
            exitosas = 0
            fallidas = 0

            for i, (venta_id, venta) in enumerate(ventas.items()):
                try:
                    factura_tns = self._convertir_formato(venta)
                    if self._insertar_factura_firebird(factura_tns):
                        # Crear registro de documento procesado
                        FudoDocumentProcessed.objects.create(
                            session_id=self.session_id,
                            fudo_original_id=str(venta_id),
                            numero_factura=factura_tns.get('numero', ''),
                            fecha=datetime.strptime(factura_tns['fecha'], '%Y-%m-%d').date() if factura_tns.get('fecha') else None,
                            nit_cliente=factura_tns['detalles'].get('nit', ''),
                            nombre_cliente=factura_tns['detalles'].get('cliente', {}).get('nombre', ''),
                            total_amount=sum(float(p.get('valuepay', 0)) for p in factura_tns['detalles'].get('payments', [])),
                            estado_insercion='success',
                            raw_data=venta
                        )
                        exitosas += 1
                    else:
                        # Crear registro con estado failed
                        FudoDocumentProcessed.objects.create(
                            session_id=self.session_id,
                            fudo_original_id=str(venta_id),
                            estado_insercion='failed',
                            error_message='Factura ya existe o no se pudo insertar',
                            raw_data=venta
                        )
                        fallidas += 1
                except Exception as e:
                    # Crear registro con error
                    try:
                        FudoDocumentProcessed.objects.create(
                            session_id=self.session_id,
                            fudo_original_id=str(venta_id),
                            estado_insercion='failed',
                            error_message=str(e),
                            raw_data=venta
                        )
                    except:
                        pass
                    fallidas += 1
                    print(f"Error procesando factura {venta_id}: {str(e)}")

                if callback:
                    callback(i + 1, total, exitosas, fallidas)

            return {
                'success': True,
                'total': total,
                'exitosas': exitosas,
                'fallidas': fallidas
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if self.firebird_conn:
                self.firebird_conn.close()

