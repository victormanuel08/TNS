#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar y mostrar el SQL que se construye a partir del payload
"""
import sys
import os
import io

# Configurar stdout para UTF-8 (evitar errores de charmap en Windows)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio manu al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'manu'))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.sistema_analitico.services.tns_query_builder import TNSQueryBuilder

# Payload del usuario
payload = {
    "empresa_servidor_id": 192,
    "table_name": "MATERIAL",
    "fields": [
        "CODIGO",
        "CODBARRA",
        "DESCRIP",
        "PESO",
        "UNIDAD",
        "GM_CODIGO",
        "GM_DESCRIP",
        "GC_CODIGO",
        "GC_DESCRIP",
        "COSTO",
        "PRECIO1",
        "PRECIO2",
        "PRECIO3",
        "PRECIO4",
        "PRECIO5",
        "DESCUENTO1",
        "DESCUENTO2",
        "DESCUENTO3",
        "DESCUENTO4",
        "DESCUENTO5",
        "MATID",
        "GRUPMATID",
        "GCMATID"
    ],
    "foreign_keys": [
        {
            "table": "MATERIALSUC",
            "localField": "MATID",
            "foreignField": "MATID",
            "columns": [
                {"name": "COSTO", "as": "COSTO"},
                {"name": "PRECIO1", "as": "PRECIO1"},
                {"name": "PRECIO2", "as": "PRECIO2"},
                {"name": "PRECIO3", "as": "PRECIO3"},
                {"name": "PRECIO4", "as": "PRECIO4"},
                {"name": "PRECIO5", "as": "PRECIO5"},
                {"name": "DESCUENTO1", "as": "DESCUENTO1"},
                {"name": "DESCUENTO2", "as": "DESCUENTO2"},
                {"name": "DESCUENTO3", "as": "DESCUENTO3"},
                {"name": "DESCUENTO4", "as": "DESCUENTO4"},
                {"name": "DESCUENTO5", "as": "DESCUENTO5"}
            ]
        },
        {
            "table": "GRUPMAT",
            "localField": "GRUPMATID",
            "foreignField": "GRUPMATID",
            "columns": [
                {"name": "CODIGO", "as": "GM_CODIGO"},
                {"name": "DESCRIP", "as": "GM_DESCRIP"}
            ]
        },
        {
            "table": "GCMAT",
            "localField": "GCMATID",
            "foreignField": "GCMATID",
            "columns": [
                {"name": "CODIGO", "as": "GC_CODIGO"},
                {"name": "DESCRIP", "as": "GC_DESCRIP"}
            ]
        }
    ],
    "order_by": [
        {
            "field": "CODIGO",
            "direction": "ASC"
        }
    ],
    "page": 1,
    "page_size": 200
}

def main():
    print("=" * 80)
    print("[SQL] GENERANDO SQL A PARTIR DEL PAYLOAD")
    print("=" * 80)
    print()
    
    # Función mock para obtener nombre real de tabla
    def get_real_table_name(table_name):
        return table_name.upper()
    
    try:
        # Construir query builder
        print("📝 Construyendo query builder...")
        query_builder = TNSQueryBuilder(
            payload['table_name'],
            get_real_table_name_func=get_real_table_name
        )
        
        print(f"   Tabla: {payload['table_name']}")
        print(f"   Campos: {len(payload.get('fields', []))}")
        print(f"   Foreign keys: {len(payload.get('foreign_keys', []))}")
        print()
        
        # Agregar componentes
        print("📋 Agregando componentes...")
        query_builder.add_fields(payload.get('fields', []))
        query_builder.add_foreign_keys(payload.get('foreign_keys', []))
        query_builder.add_filters(payload.get('filters', {}))
        query_builder.add_order_by(payload.get('order_by', []))
        query_builder.set_pagination(
            payload.get('page', 1),
            payload.get('page_size', 50)
        )
        print("   ✓ Componentes agregados")
        print()
        
        # Generar queries
        print("🔨 Generando queries SQL...")
        print()
        
        # Query de conteo
        print("=" * 80)
        print("1️⃣ QUERY DE CONTEO (COUNT)")
        print("=" * 80)
        count_query, count_params = query_builder.build_count_query()
        print(count_query)
        if count_params:
            print(f"\n[PARAMS] Parámetros: {count_params}")
        print()
        
        # Query de datos
        print("=" * 80)
        print("2. QUERY DE DATOS (SELECT)")
        print("=" * 80)
        data_query, data_params = query_builder.build_query()
        print(data_query)
        if data_params:
            print(f"\n[PARAMS] Parámetros: {data_params}")
        print()
        
        # SELECT clause detallado
        print("=" * 80)
        print("3. SELECT CLAUSE DETALLADO")
        print("=" * 80)
        select_clause, column_mapping = query_builder.build_select_clause()
        print(select_clause)
        print(f"\n[MAPPING] Column mapping: {len(column_mapping)} columnas")
        for alias, original in list(column_mapping.items())[:10]:  # Primeras 10
            print(f"   {alias} -> {original}")
        if len(column_mapping) > 10:
            print(f"   ... y {len(column_mapping) - 10} más")
        print()
        
        # JOIN clauses
        print("=" * 80)
        print("4. JOIN CLAUSES")
        print("=" * 80)
        join_clauses, alias_mapping = query_builder.build_join_clauses()
        print(join_clauses)
        print(f"\n[ALIAS] Alias mapping: {alias_mapping}")
        print()
        
        # WHERE clause
        print("=" * 80)
        print("5. WHERE CLAUSE")
        print("=" * 80)
        where_clause, where_params = query_builder.build_where_clause()
        if where_clause:
            print(where_clause)
            if where_params:
                print(f"\n[PARAMS] Parámetros: {where_params}")
        else:
            print("(Sin filtros WHERE)")
        print()
        
        # ORDER BY clause
        print("=" * 80)
        print("6. ORDER BY CLAUSE")
        print("=" * 80)
        order_by_clause = query_builder.build_order_clause()
        if order_by_clause:
            print(order_by_clause)
        else:
            print("(Sin ordenamiento)")
        print()
        
        print("=" * 80)
        print("[OK] SQL GENERADO EXITOSAMENTE")
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

