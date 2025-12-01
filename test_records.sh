#!/bin/bash
# Script para probar el endpoint records con el payload del usuario

curl -X POST http://localhost:8001/api/tns/records/ \
  -H "Content-Type: application/json" \
  -H "Api-Key: sk_Ben0l9No0lzO_VuCBT0xlZnQSDukhSRBiYhOiitdEHU" \
  -d '{
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
}'

