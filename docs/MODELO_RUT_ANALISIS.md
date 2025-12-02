# Análisis del Modelo RUT (Registro Único Tributario)

## 📄 Descripción del Documento

**Archivo**: `RUT.pdf`  
**Ubicación**: Raíz del proyecto TNSFULL  
**Tipo**: Documento de identificación tributaria colombiano

---

## 🔍 Campos Identificados (Análisis Teórico)

Basado en la estructura estándar de un RUT colombiano, estos son los campos que típicamente contiene:

### 1. **Información de Identificación**

#### Datos Principales:
- **Número de Identificación Tributaria (NIT)**: Número único de identificación
- **DV (Dígito de Verificación)**: Dígito verificador del NIT
- **Razón Social**: Nombre legal de la empresa
- **Nombre Comercial**: Nombre comercial (si aplica)

#### Fechas:
- **Fecha de Matrícula**: Fecha de registro inicial
- **Fecha de Renovación**: Última fecha de renovación
- **Fecha de Vencimiento**: Fecha de vencimiento del RUT

### 2. **Información de Ubicación**

- **Dirección Principal**: Dirección de la sede principal
- **Ciudad**: Ciudad donde está ubicada
- **Departamento**: Departamento
- **Código Postal**: Código postal (si aplica)
- **Teléfono**: Teléfono principal
- **Email**: Correo electrónico

### 3. **Información Tributaria**

- **Régimen Tributario**: 
  - Régimen Simplificado
  - Régimen Común
  - Gran Contribuyente
  - Autorretenedor
- **Actividad Económica Principal (CIIU)**: Código CIIU
- **Descripción Actividad**: Descripción de la actividad económica
- **Responsable de IVA**: Sí/No
- **Auto-retenedor**: Sí/No

### 4. **Información de Representación Legal**

- **Representante Legal**: Nombre completo
- **Tipo de Documento**: CC, NIT, CE, etc.
- **Número de Documento**: Número de identificación
- **Cargo**: Cargo del representante

### 5. **Información de Establecimientos**

- **Número de Establecimientos**: Cantidad de sucursales
- **Lista de Establecimientos**: 
  - Dirección
  - Ciudad
  - Actividad económica

### 6. **Información de Facturación**

- **Resolución de Facturación**: Número de resolución
- **Rango de Numeración**: Desde - Hasta
- **Prefijo**: Prefijo de facturación
- **Fecha de Resolución**: Fecha de la resolución

### 7. **Información Adicional**

- **Estado**: Activo, Inactivo, Cancelado
- **Categoría**: Micro, Pequeña, Mediana, Grande
- **Tamaño de Empresa**: Basado en activos o ingresos

---

## 💾 Modelo Propuesto para Base de Datos

```python
# models.py

class RUT(models.Model):
    """
    Modelo para almacenar información del Registro Único Tributario (RUT)
    de empresas colombianas.
    """
    
    # Relación con EmpresaServidor
    empresa_servidor = models.OneToOneField(
        EmpresaServidor,
        on_delete=models.CASCADE,
        related_name='rut',
        null=True,
        blank=True,
        help_text='Empresa asociada a este RUT'
    )
    
    # ========== IDENTIFICACIÓN ==========
    nit = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text='Número de Identificación Tributaria'
    )
    dv = models.CharField(
        max_length=1,
        help_text='Dígito de Verificación'
    )
    razon_social = models.CharField(
        max_length=255,
        help_text='Razón social de la empresa'
    )
    nombre_comercial = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Nombre comercial (si aplica)'
    )
    
    # ========== FECHAS ==========
    fecha_matricula = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de matrícula inicial'
    )
    fecha_renovacion = models.DateField(
        null=True,
        blank=True,
        help_text='Última fecha de renovación'
    )
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de vencimiento del RUT'
    )
    
    # ========== UBICACIÓN ==========
    direccion_principal = models.TextField(
        help_text='Dirección de la sede principal'
    )
    ciudad = models.CharField(
        max_length=100,
        help_text='Ciudad'
    )
    departamento = models.CharField(
        max_length=100,
        help_text='Departamento'
    )
    codigo_postal = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código postal'
    )
    telefono = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Teléfono principal'
    )
    email = models.EmailField(
        null=True,
        blank=True,
        help_text='Correo electrónico'
    )
    
    # ========== INFORMACIÓN TRIBUTARIA ==========
    REGIMEN_CHOICES = [
        ('simplificado', 'Régimen Simplificado'),
        ('comun', 'Régimen Común'),
        ('gran_contribuyente', 'Gran Contribuyente'),
        ('autorretenedor', 'Autorretenedor'),
    ]
    
    regimen_tributario = models.CharField(
        max_length=50,
        choices=REGIMEN_CHOICES,
        null=True,
        blank=True,
        help_text='Régimen tributario'
    )
    
    actividad_economica_ciiu = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código CIIU de actividad económica'
    )
    actividad_economica_descripcion = models.TextField(
        null=True,
        blank=True,
        help_text='Descripción de la actividad económica'
    )
    
    responsable_iva = models.BooleanField(
        default=False,
        help_text='Es responsable de IVA'
    )
    autorretenedor = models.BooleanField(
        default=False,
        help_text='Es autorretenedor'
    )
    
    # ========== REPRESENTANTE LEGAL ==========
    representante_legal_nombre = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Nombre completo del representante legal'
    )
    representante_legal_tipo_doc = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Tipo de documento (CC, NIT, CE, etc.)'
    )
    representante_legal_numero_doc = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Número de documento del representante'
    )
    representante_legal_cargo = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Cargo del representante legal'
    )
    
    # ========== FACTURACIÓN ==========
    resolucion_facturacion = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Número de resolución de facturación'
    )
    rango_facturacion_desde = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Rango de numeración desde'
    )
    rango_facturacion_hasta = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Rango de numeración hasta'
    )
    prefijo_facturacion = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Prefijo de facturación'
    )
    fecha_resolucion_facturacion = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de la resolución de facturación'
    )
    
    # ========== ESTADO Y CATEGORÍA ==========
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('cancelado', 'Cancelado'),
    ]
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo',
        help_text='Estado del RUT'
    )
    
    CATEGORIA_CHOICES = [
        ('micro', 'Microempresa'),
        ('pequena', 'Pequeña'),
        ('mediana', 'Mediana'),
        ('grande', 'Grande'),
    ]
    
    categoria_empresa = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        null=True,
        blank=True,
        help_text='Categoría de la empresa'
    )
    
    # ========== METADATOS ==========
    numero_establecimientos = models.IntegerField(
        default=0,
        help_text='Número de establecimientos'
    )
    
    # Archivo PDF original
    archivo_pdf = models.FileField(
        upload_to='ruts/',
        null=True,
        blank=True,
        help_text='Archivo PDF del RUT original'
    )
    
    # Información adicional en JSON
    informacion_adicional = models.JSONField(
        default=dict,
        blank=True,
        help_text='Información adicional no estructurada'
    )
    
    # ========== AUDITORÍA ==========
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_ultima_consulta_dian = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Última vez que se consultó en DIAN'
    )
    
    class Meta:
        db_table = 'ruts'
        verbose_name = 'RUT'
        verbose_name_plural = 'RUTs'
        indexes = [
            models.Index(fields=['nit']),
            models.Index(fields=['razon_social']),
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        return f"{self.razon_social} - NIT: {self.nit}-{self.dv}"


class EstablecimientoRUT(models.Model):
    """
    Establecimientos adicionales de una empresa (sucursales)
    """
    rut = models.ForeignKey(
        RUT,
        on_delete=models.CASCADE,
        related_name='establecimientos',
        help_text='RUT al que pertenece este establecimiento'
    )
    
    nombre = models.CharField(
        max_length=255,
        help_text='Nombre del establecimiento'
    )
    direccion = models.TextField(
        help_text='Dirección del establecimiento'
    )
    ciudad = models.CharField(
        max_length=100,
        help_text='Ciudad'
    )
    departamento = models.CharField(
        max_length=100,
        help_text='Departamento'
    )
    actividad_economica_ciiu = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código CIIU'
    )
    actividad_economica_descripcion = models.TextField(
        null=True,
        blank=True,
        help_text='Descripción de la actividad'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rut_establecimientos'
        verbose_name = 'Establecimiento RUT'
        verbose_name_plural = 'Establecimientos RUT'
    
    def __str__(self):
        return f"{self.nombre} - {self.ciudad}"

```

---

## 🔧 Campos Extraíbles del PDF

### Extracción Automática (OCR/PDF Parsing):

1. **Campos de Texto Estructurado**:
   - NIT y DV
   - Razón Social
   - Dirección
   - Teléfono
   - Email
   - Fechas

2. **Campos de Tablas**:
   - Actividades económicas (CIIU)
   - Establecimientos
   - Rangos de facturación

3. **Campos de Checkboxes/Selección**:
   - Régimen tributario
   - Responsable de IVA
   - Auto-retenedor
   - Estado

### Extracción Manual/Revisión:

1. **Información Compleja**:
   - Representante legal (puede estar en diferentes formatos)
   - Resoluciones de facturación (formato variable)
   - Información adicional en notas al pie

---

## 📋 Funcionalidades Sugeridas

### 1. **Carga de RUT**:
- Subir PDF del RUT
- Extracción automática con OCR
- Validación de campos
- Asociación con EmpresaServidor

### 2. **Consulta DIAN**:
- Integración con API de DIAN (si está disponible)
- Actualización automática de datos
- Validación de NIT

### 3. **Gestión**:
- CRUD completo desde admin
- Búsqueda por NIT, razón social
- Visualización del PDF original
- Historial de cambios

### 4. **Validaciones**:
- Validar formato de NIT
- Validar dígito verificador
- Validar fechas
- Validar formato de email/teléfono

---

## ⚠️ Nota Importante

**Este modelo es solo una propuesta teórica** basada en la estructura estándar de un RUT colombiano. 

**Para crear el modelo real, necesito:**
1. Ver el contenido real del PDF `RUT.pdf`
2. Identificar los campos exactos que contiene
3. Ajustar el modelo según la estructura real del documento

**Por favor, comparte:**
- Una descripción del contenido del PDF
- O capturas de pantalla de las secciones principales
- O el texto extraído del PDF

Con esa información, puedo crear el modelo exacto que necesitas.

