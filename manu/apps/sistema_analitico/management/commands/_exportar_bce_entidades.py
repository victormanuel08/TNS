#!/usr/bin/env python
"""
Script auxiliar para exportar datos de Entities y PasswordsEntities desde BCE.
Este script se ejecuta con la configuración de BCE.
"""
import os
import sys
import json
import django

# Configurar Django para BCE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Entities, PasswordsEntities, Third
from django.db import connection

def exportar_entidades():
    """Exporta todas las Entities a JSON"""
    entities = Entities.objects.all()
    data = []
    for entity in entities:
        data.append({
            'id': entity.id,
            'name': entity.name,
            'sigla': getattr(entity, 'sigla', '') if hasattr(entity, 'sigla') else '',
        })
    return data

def exportar_passwords_entities():
    """Exporta todas las PasswordsEntities con información relacionada"""
    passwords = PasswordsEntities.objects.select_related('entity', 'third').all()
    data = []
    for pwd in passwords:
        entity_data = {
            'id': pwd.entity.id,
            'name': pwd.entity.name,
            'sigla': getattr(pwd.entity, 'sigla', '') if hasattr(pwd.entity, 'sigla') else '',
        } if pwd.entity else None
        
        third_data = {
            'id': pwd.third.id,
            'id_number': pwd.third.id_number,
        } if pwd.third else None
        
        data.append({
            'id': pwd.id,
            'user': pwd.user,
            'password': pwd.password,
            'description': getattr(pwd, 'description', '') if hasattr(pwd, 'description') else '',
            'entity': entity_data,
            'third': third_data,
        })
    return data

if __name__ == '__main__':
    output = {
        'entities': exportar_entidades(),
        'passwords_entities': exportar_passwords_entities(),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

