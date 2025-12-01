"""
Constructor seguro de consultas SQL para Firebird
Evita inyección SQL y construye queries dinámicas de forma segura
"""
from typing import Any, Dict, List, Optional, Tuple
import re


class TNSQueryBuilder:
    """Constructor seguro de queries SQL para Firebird - EXACTAMENTE como BCE"""
    
    # Tablas comunes de TNS (referencia, pero no restrictivo)
    # El whitelist se usa solo para validación de formato, no para restringir
    COMMON_TABLES = {
        'KARDEX', 'DEKARDEX', 'TERCEROS', 'ARTICULO', 'ARTICULOS',
        'DOCUMENTO', 'RECIBO', 'MOVIMIENTO', 'BODEGA', 'BODEGAS',
        'CENTRO', 'CENTROS', 'CONCEPTO', 'CONCEPTOS', 'BANCO', 'BANCOS',
        'AREA', 'AREAS', 'SUCURSAL', 'SUCURSALES', 'ZONA', 'ZONAS',
        'PREFIJO', 'PREFIJOS', 'CONSECUTIVO', 'CONSECUTIVOS', 'MATERIAL', 'MOVI', 'DEMOVI'
    }
    
    # Operadores SQL seguros
    SAFE_OPERATORS = ['=', '!=', '<', '>', '<=', '>=', 'LIKE', 'CONTAINING', 'STARTING WITH']
    
    def __init__(self, table_name: str, get_real_table_name_func=None):
        """
        Inicializa el builder
        get_real_table_name_func: función opcional para obtener el nombre real de la tabla (como BCE)
        """
        self.table_name = self._validate_table_name(table_name)
        self.get_real_table_name = get_real_table_name_func or (lambda x: x.upper())
        self.fields: List[str] = []
        self.foreign_keys: List[Dict[str, Any]] = []
        self.filters: Dict[str, Any] = {}
        self.order_by: List[Dict[str, str]] = []
        self.page: int = 1
        self.page_size: int = 50
    
    def _validate_table_name(self, name: str) -> str:
        """Valida que el nombre de tabla sea seguro (solo formato, no whitelist)"""
        name_upper = name.strip().upper()
        # Validar formato: solo letras, números y guiones bajos, empezando con letra
        if not re.match(r'^[A-Z_][A-Z0-9_]*$', name_upper):
            raise ValueError(f"Nombre de tabla inválido: {name}")
        # No restringir por whitelist - permitir cualquier tabla válida de Firebird
        return name_upper
    
    def _validate_field_name(self, field: str) -> str:
        """Valida que el nombre de campo sea seguro"""
        field_upper = field.strip().upper()
        if not re.match(r'^[A-Z_][A-Z0-9_]*$', field_upper):
            raise ValueError(f"Nombre de campo inválido: {field}")
        return field_upper
    
    def add_fields(self, fields: List[str]):
        """Agrega campos a seleccionar"""
        self.fields = [self._validate_field_name(f) for f in fields]
        return self
    
    def add_foreign_keys(self, foreign_keys: List[Dict[str, Any]]):
        """Agrega relaciones (JOINs) - Soporta JOINs encadenados y tipos de JOIN"""
        validated_fks = []
        for fk in foreign_keys:
            # Validar tipo de JOIN
            join_type = fk.get('joinType', 'LEFT').upper()
            if join_type not in ['INNER', 'LEFT', 'RIGHT', 'FULL']:
                raise ValueError(f"Tipo de JOIN inválido: {join_type}. Debe ser INNER, LEFT, RIGHT o FULL")
            
            validated_fk = {
                'table': self._validate_table_name(fk['table']),
                'localField': self._validate_field_name(fk['localField']),
                'foreignField': self._validate_field_name(fk['foreignField']),
                'joinType': join_type,
                'joinFrom': fk.get('joinFrom'),  # Tabla desde la cual hacer el JOIN (opcional)
                'columns': [
                    {
                        'name': self._validate_field_name(col['name']),
                        'as': self._validate_field_name(col.get('as', col['name']))
                    }
                    for col in fk.get('columns', [])
                ]
            }
            validated_fks.append(validated_fk)
        self.foreign_keys = validated_fks
        return self
    
    def add_filters(self, filters: Dict[str, Any]):
        """Agrega filtros WHERE de forma segura"""
        self.filters = filters
        return self
    
    def add_order_by(self, order_by: List[Dict[str, str]]):
        """Agrega ordenamiento"""
        validated_order = []
        for order in order_by:
            validated_order.append({
                'field': self._validate_field_name(order['field']),
                'direction': order.get('direction', 'ASC').upper()
            })
            if validated_order[-1]['direction'] not in ['ASC', 'DESC']:
                raise ValueError("Dirección de ordenamiento debe ser ASC o DESC")
        self.order_by = validated_order
        return self
    
    def set_pagination(self, page: int, page_size: int):
        """Configura paginación"""
        if page < 1:
            raise ValueError("Página debe ser >= 1")
        if page_size < 1 or page_size > 500:
            raise ValueError("Tamaño de página debe estar entre 1 y 500")
        self.page = page
        self.page_size = page_size
        return self
    
    def build_select_clause(self) -> Tuple[str, Dict[str, str]]:
        """Construye la cláusula SELECT"""
        import logging
        logger = logging.getLogger(__name__)
        
        selected_columns = []
        column_mapping = {}
        
        # Si no hay campos especificados, usar todos
        if not self.fields:
            return 'a.*', {}
        
        # Debug: verificar foreign_keys
        logger.debug(f'Fields: {self.fields}')
        logger.debug(f'Foreign keys: {self.foreign_keys}')
        
        # Campos principales
        for field in self.fields:
            # Verificar si es campo de FK (exactamente como BCE)
            is_fk_field = any(
                field == fk_col.get('as')
                for fk in self.foreign_keys
                for fk_col in fk.get('columns', [])
            )
            
            logger.debug(f'Field {field}: is_fk_field={is_fk_field}')
            
            # Solo agregar campos que NO son de foreign key
            if not is_fk_field:
                selected_columns.append(f'a.{field}')
                column_mapping[field] = field
        
        # Campos de foreign keys
        table_alias_counter = {}
        for fk in self.foreign_keys:
            # Generar alias único basado en tabla y campo local (como BCE)
            base_alias = f"fk_{fk['table'][:3]}_{fk['localField'][:5]}".replace('"', '').replace(' ', '')
            
            if base_alias in table_alias_counter:
                table_alias_counter[base_alias] += 1
                table_alias = f"{base_alias}_{table_alias_counter[base_alias]}"
            else:
                table_alias_counter[base_alias] = 1
                table_alias = base_alias
            
            for col in fk.get('columns', []):
                alias = col.get('as')
                if alias in self.fields:
                    selected_columns.append(f'{table_alias}.{col["name"]} AS {alias}')
                    column_mapping[alias] = col['name']
        
        # Si no hay columnas seleccionadas, usar todas las de la tabla principal
        if not selected_columns:
            return 'a.*', {}
        
        return ', '.join(selected_columns), column_mapping
    
    def build_join_clauses(self) -> Tuple[str, Dict[str, str]]:
        """Construye las cláusulas JOIN - Soporta JOINs encadenados y tipos de JOIN"""
        join_clauses = []
        alias_mapping = {}
        table_alias_counter = {}
        
        for fk in self.foreign_keys:
            # Generar alias único basado en tabla y campo local (como BCE)
            base_alias = f"fk_{fk['table'][:3]}_{fk['localField'][:5]}".replace('"', '').replace(' ', '')
            
            if base_alias in table_alias_counter:
                table_alias_counter[base_alias] += 1
                table_alias = f"{base_alias}_{table_alias_counter[base_alias]}"
            else:
                table_alias_counter[base_alias] = 1
                table_alias = base_alias
            
            alias_mapping[fk['table']] = table_alias
            
            # Determinar tipo de JOIN (default: LEFT para retrocompatibilidad)
            join_type = fk.get('joinType', 'LEFT').upper()
            
            # Determinar desde qué tabla hacer el JOIN
            join_from_table = fk.get('joinFrom')
            if join_from_table:
                # JOIN encadenado: buscar el alias de la tabla padre
                parent_alias = None
                # Buscar en alias_mapping por nombre de tabla
                for table_name, alias in alias_mapping.items():
                    if table_name.upper() == join_from_table.upper():
                        parent_alias = alias
                        break
                
                if not parent_alias:
                    raise ValueError(f"No se encontró la tabla padre '{join_from_table}' para el JOIN encadenado. Asegúrate de que la tabla padre esté definida antes en foreign_keys.")
                
                # JOIN desde tabla padre (encadenado)
                join_clauses.append(
                    f'{join_type} JOIN {fk["table"]} {table_alias} '
                    f'ON {parent_alias}.{fk["localField"]} = {table_alias}.{fk["foreignField"]}'
                )
            else:
                # JOIN directo desde tabla principal (comportamiento original - retrocompatible)
                join_clauses.append(
                    f'{join_type} JOIN {fk["table"]} {table_alias} '
                    f'ON a.{fk["localField"]} = {table_alias}.{fk["foreignField"]}'
                )
        
        return ' '.join(join_clauses), alias_mapping
    
    def _get_fk_alias_and_field(self, field_name: str) -> Tuple[str | None, str | None]:
        """
        Detecta si un campo es de foreign key y retorna el alias de la tabla FK y el nombre del campo original.
        Retorna (alias, original_field) o (None, None) si no es FK.
        """
        # Buscar si el campo corresponde a un alias de foreign key
        table_alias_counter = {}
        for fk in self.foreign_keys:
            # Generar alias único (igual que en build_join_clauses)
            base_alias = f"fk_{fk['table'][:3]}_{fk['localField'][:5]}".replace('"', '').replace(' ', '')
            
            if base_alias in table_alias_counter:
                table_alias_counter[base_alias] += 1
                table_alias = f"{base_alias}_{table_alias_counter[base_alias]}"
            else:
                table_alias_counter[base_alias] = 1
                table_alias = base_alias
            
            # Verificar si el campo coincide con algún alias de columna FK
            for col in fk.get('columns', []):
                alias = col.get('as', '').upper()
                if alias == field_name.upper():
                    # Es un campo de foreign key, retornar alias de tabla y nombre original del campo
                    return table_alias, col['name'].upper()
        
        # Buscar si el campo coincide con el nombre de la tabla FK (para filtros por defecto)
        # Ejemplo: si filtro es "KARDEX.CODCOMP" y hay FK a KARDEX
        field_upper = field_name.upper()
        table_alias_counter = {}
        for fk in self.foreign_keys:
            fk_table_upper = fk['table'].upper()
            # Verificar si el campo empieza con el nombre de la tabla FK
            # Ejemplo: "KARDEX_CODCOMP" -> tabla "KARDEX", campo "CODCOMP"
            if field_upper.startswith(fk_table_upper + '_'):
                # Generar alias único
                base_alias = f"fk_{fk['table'][:3]}_{fk['localField'][:5]}".replace('"', '').replace(' ', '')
                
                if base_alias in table_alias_counter:
                    table_alias_counter[base_alias] += 1
                    table_alias = f"{base_alias}_{table_alias_counter[base_alias]}"
                else:
                    table_alias_counter[base_alias] = 1
                    table_alias = base_alias
                
                # Extraer nombre del campo (sin el prefijo de tabla)
                original_field = field_upper[len(fk_table_upper) + 1:]
                return table_alias, original_field
        
        return None, None
    
    def build_where_clause(self) -> Tuple[str, List[Any]]:
        """Construye la cláusula WHERE de forma segura, manejando foreign keys"""
        where_parts = []
        params = []
        
        if not self.filters:
            return '', []
        
        for field, condition in self.filters.items():
            if field == 'OR':
                continue
            
            field_validated = self._validate_field_name(field)
            
            # Detectar si es campo de foreign key
            fk_alias, original_field = self._get_fk_alias_and_field(field)
            
            # Si es FK, usar alias de tabla FK; si no, usar tabla principal
            table_prefix = f"{fk_alias}." if fk_alias else "a."
            field_to_use = original_field if fk_alias and original_field else field_validated
            
            if isinstance(condition, dict):
                # Filtros con operadores
                if 'operator' in condition and 'value' in condition:
                    operator = condition['operator'].upper().strip()
                    if operator not in self.SAFE_OPERATORS:
                        raise ValueError(f"Operador no permitido: {operator}")
                    
                    where_parts.append(f'{table_prefix}{field_to_use} {operator} ?')
                    params.append(condition['value'])
                
                # Filtros de texto
                elif 'contains' in condition:
                    where_parts.append(f'{table_prefix}{field_to_use} CONTAINING ?')
                    params.append(f"{condition['contains']}")
                elif 'startsWith' in condition:
                    where_parts.append(f'{table_prefix}{field_to_use} STARTING WITH ?')
                    params.append(f"{condition['startsWith']}%")
                
                # Filtros de rango
                elif 'between' in condition:
                    start, end = condition['between']
                    where_parts.append(f'{table_prefix}{field_to_use} BETWEEN ? AND ?')
                    params.extend([start, end])
                
                # Filtros de tiempo (VARCHAR) - como BCE
                elif 'time' in condition:
                    time_cond = condition['time']
                    if isinstance(time_cond, dict):
                        if 'between' in time_cond:
                            start, end = time_cond['between']
                            where_parts.append(f'a.{field_validated} BETWEEN ? AND ?')
                            params.extend([start, end])
                        elif 'eq' in time_cond:
                            where_parts.append(f'a.{field_validated} = ?')
                            params.append(time_cond['eq'])
                        elif 'gt' in time_cond:
                            where_parts.append(f'a.{field_validated} > ?')
                            params.append(time_cond['gt'])
                        elif 'lt' in time_cond:
                            where_parts.append(f'a.{field_validated} < ?')
                            params.append(time_cond['lt'])
                
                # Filtros de lista (IN)
                elif 'in' in condition:
                    values = condition['in']
                    if not isinstance(values, list):
                        raise ValueError("El valor de 'in' debe ser una lista")
                    if values:
                        placeholders = ','.join(['?' for _ in values])
                        where_parts.append(f'{table_prefix}{field_to_use} IN ({placeholders})')
                        params.extend(values)
            else:
                # Igualdad directa
                where_parts.append(f'{table_prefix}{field_to_use} = ?')
                params.append(condition)
        
        # Manejar filtros OR
        if 'OR' in self.filters:
            or_conditions = []
            for or_item in self.filters['OR']:
                if isinstance(or_item, dict):
                    for field, condition in or_item.items():
                        field_validated = self._validate_field_name(field)
                        
                        # Detectar si es campo de foreign key
                        fk_alias, original_field = self._get_fk_alias_and_field(field)
                        table_prefix = f"{fk_alias}." if fk_alias else "a."
                        field_to_use = original_field if fk_alias and original_field else field_validated
                        
                        if isinstance(condition, dict):
                            if 'contains' in condition:
                                or_conditions.append(f'{table_prefix}{field_to_use} CONTAINING ?')
                                params.append(f"{condition['contains']}")
                            elif 'startsWith' in condition:
                                or_conditions.append(f'{table_prefix}{field_to_use} STARTING WITH ?')
                                params.append(f"{condition['startsWith']}%")
                            elif 'operator' in condition and 'value' in condition:
                                operator = condition['operator']
                                value = condition['value']
                                if operator.strip() in ['>', '<', '>=', '<=', '=', '!=']:
                                    or_conditions.append(f'{table_prefix}{field_to_use} {operator} ?')
                                    params.append(value)
                            elif 'between' in condition:
                                start, end = condition['between']
                                or_conditions.append(f'({table_prefix}{field_to_use} BETWEEN ? AND ?)')
                                params.extend([start, end])
                            elif 'time' in condition:
                                time_cond = condition['time']
                                if isinstance(time_cond, dict):
                                    if 'between' in time_cond:
                                        start, end = time_cond['between']
                                        or_conditions.append(f'(a.{field_validated} BETWEEN ? AND ?)')
                                        params.extend([start, end])
                                    elif 'eq' in time_cond:
                                        or_conditions.append(f'{table_prefix}{field_to_use} = ?')
                                        params.append(time_cond['eq'])
                                    elif 'gt' in time_cond:
                                        or_conditions.append(f'{table_prefix}{field_to_use} > ?')
                                        params.append(time_cond['gt'])
                                    elif 'lt' in time_cond:
                                        or_conditions.append(f'{table_prefix}{field_to_use} < ?')
                                        params.append(time_cond['lt'])
                        else:
                            # Igualdad exacta para valores directos
                            or_conditions.append(f'{table_prefix}{field_to_use} = ?')
                            params.append(condition)
            
            if or_conditions:
                where_parts.append(f"({' OR '.join(or_conditions)})")
        
        where_clause = ' AND '.join(where_parts) if where_parts else ''
        return where_clause, params
    
    def build_order_clause(self) -> str:
        """Construye la cláusula ORDER BY (exactamente como BCE)"""
        if not self.order_by:
            return ''
        
        order_parts = []
        for order in self.order_by:
            if isinstance(order, dict):
                # Formato: {"field": "nombre", "direction": "ASC|DESC"}
                field = self._validate_field_name(order['field'])
                direction = order.get('direction', 'ASC').upper()
                if direction not in ['ASC', 'DESC']:
                    direction = 'ASC'
                
                # Verificar si el campo es de foreign key
                fk_alias, original_field = self._get_fk_alias_and_field(field)
                
                if fk_alias:
                    # Campo de FK: usar alias de tabla FK (sin comillas)
                    order_parts.append(f'{fk_alias}.{original_field} {direction}')
                else:
                    # Campo principal: usar alias de tabla principal (sin comillas)
                    order_parts.append(f'a.{field} {direction}')
            elif isinstance(order, str):
                # Formato legacy: "field_DESC" o "field"
                if order.endswith('_DESC'):
                    field = order[:-5]
                    order_parts.append(f'a.{field} DESC')
                else:
                    order_parts.append(f'a.{order} ASC')
        
        return 'ORDER BY ' + ', '.join(order_parts)
    
    def build_base_query(self) -> Tuple[str, List[Any]]:
        """Construye la query base completa (sin paginación) - EXACTAMENTE como BCE"""
        # Obtener nombre real de la tabla (como BCE)
        real_table_name = self.get_real_table_name(self.table_name)
        
        select_clause, _ = self.build_select_clause()
        join_clauses_list = []
        join_clause_str, _ = self.build_join_clauses()
        if join_clause_str:
            join_clauses_list.append(join_clause_str)
        where_clause, params = self.build_where_clause()
        order_clause = self.build_order_clause()
        
        # Construir query base (EXACTAMENTE como BCE)
        base_query = f"""
            SELECT {select_clause}
            FROM {real_table_name} a
            {' '.join(join_clauses_list)}
            {f"WHERE {where_clause}" if where_clause else ""}
            {order_clause if order_clause else ""}
        """
        
        return base_query.strip(), params
    
    def build_query(self) -> Tuple[str, List[Any]]:
        """Construye la query SQL paginada usando subquery (EXACTAMENTE como BCE)"""
        base_query, params = self.build_base_query()
        
        # Paginación Firebird usando subquery (EXACTAMENTE como BCE)
        offset = (self.page - 1) * self.page_size
        paginated_query = f"SELECT FIRST {self.page_size} SKIP {offset} * FROM ({base_query})"
        
        return paginated_query, params
    
    def build_count_query(self) -> Tuple[str, List[Any]]:
        """Construye query para contar total usando subquery (EXACTAMENTE como BCE)"""
        base_query, params = self.build_base_query()
        
        # COUNT usando subquery (EXACTAMENTE como BCE)
        count_query = f'SELECT COUNT(*) FROM ({base_query})'
        
        return count_query, params

