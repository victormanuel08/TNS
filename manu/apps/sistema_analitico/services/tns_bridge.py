import hashlib
import os
from datetime import date
from typing import Any, Dict, Iterable, List, Optional

import firebirdsql

from apps.sistema_analitico.models import EmpresaServidor


class TNSBridge:
    """
    Conector reutilizable para bases TNS (Firebird) usando la información que
    ya tenemos en EmpresaServidor / Servidor.
    """

    _schema_cache: Dict[str, Dict[str, str]] = {}
    _connection_pool: Dict[str, firebirdsql.Connection] = {}

    def __init__(self, empresa: EmpresaServidor):
        self.empresa = empresa
        self.servidor = empresa.servidor
        if self.servidor.tipo_servidor != 'FIREBIRD':
            raise ValueError('Solo se soportan conexiones Firebird para TNS.')

        self.charset = 'WIN1252'
        self.conn: Optional[firebirdsql.Connection] = None
        self.cursor: Optional[firebirdsql.Cursor] = None

    # ------------------------------------------------------------------ utils
    @property
    def pool_key(self) -> str:
        ruta = self.empresa.ruta_base or self.servidor.ruta_maestra or ''
        return hashlib.md5(
            f"{self.servidor.host}:{self.servidor.puerto}:{self.servidor.usuario}:{ruta}".encode()
        ).hexdigest()

    @property
    def schema_cache(self) -> Dict[str, str]:
        return self._schema_cache.setdefault(self.pool_key, {})

    # ----------------------------------------------------------------- connect
    def connect(self):
        if self.conn:
            return

        os.environ['ISC_CP'] = self.charset
        port = self.servidor.puerto or 3050
        database_path = self.empresa.ruta_base or self.servidor.ruta_maestra
        if not database_path:
            raise ValueError('No se configuró la ruta de la base de datos TNS.')

        if self.pool_key in self._connection_pool:
            conn = self._connection_pool[self.pool_key]
            try:
                cur = conn.cursor()
                cur.execute('SELECT 1 FROM RDB$DATABASE')
                cur.fetchone()
                cur.close()
                self.conn = conn
            except Exception:
                try:
                    conn.close()
                finally:
                    self._connection_pool.pop(self.pool_key, None)

        if not self.conn:
            self.conn = firebirdsql.connect(
                host=self.servidor.host,
                database=database_path,
                user=self.servidor.usuario,
                password=self.servidor.password,
                port=port,
                charset=self.charset,
            )
            self._connection_pool[self.pool_key] = self.conn

        self.cursor = self.conn.cursor()

    def close(self):
        if self.cursor:
            try:
                self.cursor.close()
            finally:
                self.cursor = None
        self.conn = None

    # ----------------------------------------------------------------- helpers
    def _ensure_schema(self):
        if self.schema_cache:
            return
        self.connect()
        self.cursor.execute("""
            SELECT RDB$RELATION_NAME
            FROM RDB$RELATIONS
            WHERE RDB$SYSTEM_FLAG = 0 AND RDB$VIEW_BLR IS NULL
        """)
        self.schema_cache.update({
            name.strip().upper(): name.strip()
            for (name,) in self.cursor.fetchall()
        })

    def list_tables(self) -> List[str]:
        self._ensure_schema()
        return list(self.schema_cache.values())

    def _execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> List[Dict[str, Any]]:
        self.connect()
        self.cursor.execute(sql, params or [])
        columns = [col[0].strip() for col in self.cursor.description or []]
        rows = []
        for data in self.cursor.fetchall():
            rows.append({
                columns[idx]: self._normalize_value(value)
                for idx, value in enumerate(data)
            })
        return rows

    def _execute_non_query(self, sql: str, params: Optional[Iterable[Any]] = None) -> int:
        self.connect()
        self.cursor.execute(sql, params or [])
        self.conn.commit()
        return self.cursor.rowcount

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, bytes):
            return value.decode(self.charset, errors='ignore')
        return value

    # ------------------------------------------------------------------ public
    def run_query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        return self._execute(sql, params)

    def call_procedure(self, name: str, params: Dict[str, Any]) -> List[Any]:
        placeholders = ', '.join(['?'] * len(params))
        sql = f"SELECT * FROM {name}({placeholders})"
        return self._execute(sql, list(params.values()))

    # ---------------------------- specialized helpers ------------------------
    def get_consecutive(self, codcomp: str, codprefijo: str, sucursal: str = "00"):
        sql = "SELECT * FROM TNS_SP_CONSECUTIVO2(?, ?, ?)"
        result = self._execute(sql, [codcomp, codprefijo, sucursal])
        return result[0]['COLUMN_0'] if result else None

    def emit_invoice(self, payload: Dict[str, Any]):
        today = payload.get('fecha') or date.today()
        fecha_sql = today.strftime('%Y-%m-%d') if hasattr(today, 'strftime') else today
        codcomp = payload.get('codcomp', 'FV')
        codprefijo = payload.get('codprefijo') or payload.get('prefijo') or '00'
        sucursal = payload.get('sucursal', '00')
        numero = self.get_consecutive(codcomp, codprefijo, sucursal)

        params = [
            codcomp,
            codprefijo,
            numero,
            fecha_sql,
            payload.get('periodo') or int(str(fecha_sql)[5:7]),
            payload.get('formapago', 'CO'),
            payload.get('plazodias', 1),
            payload.get('usuario', 'ADMIN'),
            payload.get('banco', '00'),
            payload.get('nittri') or '222222222222',
            payload.get('numdocu'),
            payload.get('vid', '02'),
        ]
        sql = "SELECT * FROM TNS_INS_FACTURAVTA(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self._execute(sql, params)
        return numero

    # ----------------------------------------------------------------- cleanup
    @classmethod
    def cleanup(cls):
        for conn in list(cls._connection_pool.values()):
            try:
                conn.close()
            except Exception:
                pass
        cls._connection_pool.clear()
        cls._schema_cache.clear()
