# Carpeta de Datos para Procesamiento y Entrenamiento

Esta carpeta está destinada a almacenar archivos de datos (principalmente PDFs) utilizados para:
- Procesamiento de información (ej: CIIU.pdf)
- Entrenamiento de modelos
- Análisis y extracción de datos

## Estructura Recomendada

```
data/
├── ciiu/              # PDFs relacionados con códigos CIUU
│   └── CIIU.pdf
├── training/          # PDFs para entrenamiento de modelos
│   └── ...
├── documents/         # Otros documentos de referencia
│   └── ...
└── cache/             # Cache de procesamiento (ya existe)
    └── ...
```

## Uso

Los comandos de Django pueden acceder a estos archivos usando rutas relativas desde `manage.py`:

```bash
# Ejemplo: Procesar CIUU
python manage.py procesar_lote_ciiu_validacion --todos --pdf-path data/ciiu/CIIU.pdf
```

## Seguridad

- Los archivos `.pdf` en esta carpeta están ignorados por Git (ver `.gitignore`)
- Los PDFs grandes no se subirán al repositorio
- Solo la estructura de carpetas y este README se versionan

## ⚠️ IMPORTANTE: Subir PDFs al Servidor

**Los PDFs NO se suben automáticamente con Git.** Debes subirlos manualmente al servidor:

1. **En desarrollo local:** Coloca el PDF en la carpeta correspondiente (ej: `data/ciiu/CIIU.pdf`)
2. **En el servidor:** Sube el PDF usando FTP, SCP, o el método que uses:
   ```bash
   # Ejemplo con SCP:
   scp data/ciiu/CIIU.pdf usuario@servidor:/ruta/al/proyecto/manu/data/ciiu/
   ```

3. **Verificar en servidor:** Asegúrate de que el PDF esté en la ruta correcta antes de ejecutar los comandos:
   ```bash
   # En el servidor:
   ls -lh manu/data/ciiu/CIIU.pdf
   ```

## Nota

- La estructura de carpetas (con `.gitkeep`) SÍ se versiona en Git
- Los PDFs deben subirse directamente al servidor, NO al repositorio Git
- Esto evita que archivos grandes ocupen espacio innecesario en el repositorio

