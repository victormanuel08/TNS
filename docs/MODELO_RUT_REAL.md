# Modelo RUT - Basado en PDF Real

## 📄 Análisis del PDF RUT.pdf

He extraído el contenido del PDF y estos son los campos identificados:

### Información Principal:
- **NIT**: 9008697500
- **DV**: 0
- **Razón Social**: CONSTRUCTORES UNIDOS DEL SIGLO 21 S.A.S
- **Nombre Comercial**: CONSTRUCTORES UNIDOS DEL SIGLO 21
- **Sigla**: CONSTRUUNIDOS21 S.A S
- **Tipo de Contribuyente**: Persona jurídica
- **Número de Formulario**: 141169735821

### Ubicación:
- **País**: COLOMBIA
- **Departamento**: Norte de Santander (Código: 54)
- **Ciudad/Municipio**: Cúcuta (Código: 001)
- **Dirección Principal**: AV 15 12 11 BRR NUEVA COLOMBIA
- **Código Postal**: 131433
- **Teléfono 1**: 3143302524
- **Email**: constructoresunidossiglo21@gmail.com
- **Dirección Seccional**: Impuestos de Cúcuta

### Actividades Económicas:
- **Actividad Principal**: Código 42902 (Fecha inicio: 2015-07-01)
- **Actividad Secundaria**: Código 46592 (Fecha inicio: 2015-07-01)
- **Otras Actividades**: Código 68101
- **Número de Establecimientos**: 1

### Responsabilidades, Calidades y Atributos:
- **Códigos**: 7, 9, 14, 42, 47, 48, 52, 55
- Incluye:
  - Retención en la fuente a título de renta
  - Retención en la fuente en el impuesto
  - Informante de exogena
  - Obligado a llevar contabilidad
  - Régimen Simple de Tributación - SIM
  - Impuesto sobre las ventas - IVA
  - Facturador electrónico
  - Informante de Beneficiarios Finales

### Constitución y Registro:
- **Clase**: 04
- **Número**: 00000
- **Fecha Constitución**: 2015-07-01
- **Número de Notaría**: 03
- **Entidad de Registro**: 03
- **Fecha de Registro**: 2015-07-17
- **Matrícula Mercantil**: 278956
- **Departamento**: 54
- **Ciudad/Municipio**: 11
- **Vigencia Desde**: 2015-07-01
- **Vigencia Hasta**: 9999-12-31

### Composición del Capital:
- **Nacional**: 100.0%
- **Nacional Público**: 0.0%
- **Nacional Privado**: 100.0%
- **Extranjero**: 0%
- **Extranjero Público**: 0.0%
- **Extranjero Privado**: 0.0%

### Entidad de Vigilancia:
- **Superintendencia de Sociedades**: 5

### Representante Legal:
- **Representación**: REPRS LEGAL PRIN
- **Fecha Inicio**: 2022-04-20
- **Tipo Documento**: Cédula de Ciudadanía
- **Número Identificación**: 1388271185
- **DV**: 1
- **Nombre**: GELVEZ MARIO ALBERTO
- **Primer Apellido**: GELVEZ
- **Primer Nombre**: MARIO
- **Otros Nombres**: ALBERTO

### Establecimientos:
1. **Tipo**: Establecimiento de comercio (02)
   - **Actividad**: Construcción de otras obras de ingeniería civil (4290)
   - **Nombre**: CONSTRUCTORES UNIDOS DEL SIGLO 21
   - **Departamento**: Norte de Santander (54)
   - **Ciudad**: Cúcuta (001)
   - **Dirección**: AV 15 12 11 BRR NUEVA COLOMBIA
   - **Matrícula Mercantil**: 278957
   - **Fecha Matrícula**: 2015-07-17
   - **Teléfono**: 3133556976

---

## 💾 Modelo Django Propuesto

```python
# models.py

class RUT(models.Model):
    """
    Modelo para almacenar información del Registro Único Tributario (RUT)
    de empresas colombianas, basado en el formulario real de la DIAN.
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
    
    # ========== IDENTIFICACIÓN PRINCIPAL ==========
    numero_formulario = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Número de formulario del RUT'
    )
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
    
    # Tipo de contribuyente
    TIPO_CONTRIBUYENTE_CHOICES = [
        ('persona_juridica', 'Persona jurídica'),
        ('persona_natural', 'Persona natural'),
    ]
    tipo_contribuyente = models.CharField(
        max_length=20,
        choices=TIPO_CONTRIBUYENTE_CHOICES,
        null=True,
        blank=True,
        help_text='Tipo de contribuyente'
    )
    
    razon_social = models.CharField(
        max_length=255,
        help_text='Razón social de la empresa'
    )
    nombre_comercial = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Nombre comercial'
    )
    sigla = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Sigla de la empresa'
    )
    
    # ========== UBICACIÓN ==========
    pais = models.CharField(
        max_length=100,
        default='COLOMBIA',
        help_text='País'
    )
    departamento_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código del departamento'
    )
    departamento_nombre = models.CharField(
        max_length=100,
        help_text='Nombre del departamento'
    )
    ciudad_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código de la ciudad/municipio'
    )
    ciudad_nombre = models.CharField(
        max_length=100,
        help_text='Nombre de la ciudad/municipio'
    )
    direccion_principal = models.TextField(
        help_text='Dirección de la sede principal'
    )
    codigo_postal = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código postal'
    )
    telefono_1 = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Teléfono principal'
    )
    telefono_2 = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Teléfono secundario'
    )
    email = models.EmailField(
        null=True,
        blank=True,
        help_text='Correo electrónico'
    )
    direccion_seccional = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Dirección seccional de la DIAN'
    )
    buzon_electronico = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Buzón electrónico'
    )
    
    # ========== ACTIVIDADES ECONÓMICAS ==========
    actividad_principal_ciiu = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código CIIU de actividad principal'
    )
    actividad_principal_fecha_inicio = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de inicio de actividad principal'
    )
    actividad_secundaria_ciiu = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código CIIU de actividad secundaria'
    )
    actividad_secundaria_fecha_inicio = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de inicio de actividad secundaria'
    )
    otras_actividades_ciiu = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código CIIU de otras actividades'
    )
    numero_establecimientos = models.IntegerField(
        default=0,
        help_text='Número de establecimientos'
    )
    
    # ========== RESPONSABILIDADES Y ATRIBUTOS ==========
    # Almacenar como JSON para flexibilidad
    responsabilidades_codigos = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de códigos de responsabilidades (ej: [7, 9, 14, 42, 47, 48, 52, 55])'
    )
    responsabilidades_descripcion = models.JSONField(
        default=list,
        blank=True,
        help_text='Descripciones de las responsabilidades'
    )
    
    # Campos booleanos para responsabilidades comunes
    responsable_iva = models.BooleanField(
        default=False,
        help_text='Es responsable de IVA'
    )
    autorretenedor = models.BooleanField(
        default=False,
        help_text='Es autorretenedor'
    )
    obligado_contabilidad = models.BooleanField(
        default=False,
        help_text='Obligado a llevar contabilidad'
    )
    regimen_simple = models.BooleanField(
        default=False,
        help_text='Régimen Simple de Tributación - SIM'
    )
    facturador_electronico = models.BooleanField(
        default=False,
        help_text='Facturador electrónico'
    )
    informante_exogena = models.BooleanField(
        default=False,
        help_text='Informante de exogena'
    )
    informante_beneficiarios_finales = models.BooleanField(
        default=False,
        help_text='Informante de Beneficiarios Finales'
    )
    
    # ========== CONSTITUCIÓN Y REGISTRO ==========
    constitucion_clase = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Clase de constitución'
    )
    constitucion_numero = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Número de constitución'
    )
    constitucion_fecha = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de constitución'
    )
    constitucion_notaria = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Número de notaría'
    )
    registro_entidad = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Entidad de registro'
    )
    registro_fecha = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de registro'
    )
    matricula_mercantil = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Número de matrícula mercantil'
    )
    registro_departamento = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código departamento de registro'
    )
    registro_ciudad = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código ciudad de registro'
    )
    vigencia_desde = models.DateField(
        null=True,
        blank=True,
        help_text='Vigencia desde'
    )
    vigencia_hasta = models.DateField(
        null=True,
        blank=True,
        help_text='Vigencia hasta'
    )
    
    # ========== COMPOSICIÓN DEL CAPITAL ==========
    capital_nacional_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital nacional'
    )
    capital_nacional_publico_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital nacional público'
    )
    capital_nacional_privado_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital nacional privado'
    )
    capital_extranjero_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital extranjero'
    )
    capital_extranjero_publico_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital extranjero público'
    )
    capital_extranjero_privado_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital extranjero privado'
    )
    
    # ========== ENTIDAD DE VIGILANCIA ==========
    entidad_vigilancia = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Entidad de vigilancia y control'
    )
    entidad_vigilancia_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código de entidad de vigilancia'
    )
    
    # ========== REPRESENTANTE LEGAL ==========
    representante_legal_representacion = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Tipo de representación'
    )
    representante_legal_fecha_inicio = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha inicio ejercicio representación'
    )
    representante_legal_tipo_doc = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Tipo de documento'
    )
    representante_legal_numero_doc = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Número de identificación'
    )
    representante_legal_dv = models.CharField(
        max_length=1,
        null=True,
        blank=True,
        help_text='Dígito verificador'
    )
    representante_legal_tarjeta_profesional = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Número de tarjeta profesional'
    )
    representante_legal_primer_apellido = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Primer apellido'
    )
    representante_legal_segundo_apellido = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Segundo apellido'
    )
    representante_legal_primer_nombre = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Primer nombre'
    )
    representante_legal_otros_nombres = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Otros nombres'
    )
    representante_legal_nit = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='NIT del representante legal'
    )
    representante_legal_razon_social = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Razón social del representante legal'
    )
    
    # ========== VINCULACIÓN ECONÓMICA ==========
    vinculacion_economica = models.BooleanField(
        default=False,
        help_text='Tiene vinculación económica'
    )
    grupo_economico_nombre = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Nombre del grupo económico y/o empresarial'
    )
    matriz_nit = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='NIT de la matriz o controlante'
    )
    matriz_dv = models.CharField(
        max_length=1,
        null=True,
        blank=True,
        help_text='DV de la matriz'
    )
    matriz_razon_social = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Razón social de la matriz o controlante'
    )
    
    # ========== ARCHIVO Y METADATOS ==========
    archivo_pdf = models.FileField(
        upload_to='ruts/',
        null=True,
        blank=True,
        help_text='Archivo PDF del RUT original'
    )
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
            models.Index(fields=['ciudad_nombre']),
        ]
    
    def __str__(self):
        return f"{self.razon_social} - NIT: {self.nit}-{self.dv}"


class EstablecimientoRUT(models.Model):
    """
    Establecimientos adicionales de una empresa (sucursales, agencias, etc.)
    """
    rut = models.ForeignKey(
        RUT,
        on_delete=models.CASCADE,
        related_name='establecimientos',
        help_text='RUT al que pertenece este establecimiento'
    )
    
    tipo_establecimiento = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Tipo de establecimiento (ej: Establecimiento de comercio)'
    )
    tipo_establecimiento_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código del tipo de establecimiento'
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
    nombre = models.CharField(
        max_length=255,
        help_text='Nombre del establecimiento'
    )
    departamento_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código del departamento'
    )
    departamento_nombre = models.CharField(
        max_length=100,
        help_text='Nombre del departamento'
    )
    ciudad_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código de la ciudad/municipio'
    )
    ciudad_nombre = models.CharField(
        max_length=100,
        help_text='Nombre de la ciudad/municipio'
    )
    direccion = models.TextField(
        help_text='Dirección del establecimiento'
    )
    matricula_mercantil = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Número de matrícula mercantil'
    )
    fecha_matricula_mercantil = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de la matrícula mercantil'
    )
    telefono = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Teléfono del establecimiento'
    )
    fecha_cierre = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de cierre (si aplica)'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rut_establecimientos'
        verbose_name = 'Establecimiento RUT'
        verbose_name_plural = 'Establecimientos RUT'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.ciudad_nombre}"


class EstadoRUT(models.Model):
    """
    Historial de estados del RUT
    """
    rut = models.ForeignKey(
        RUT,
        on_delete=models.CASCADE,
        related_name='estados',
        help_text='RUT al que pertenece este estado'
    )
    
    estado_codigo = models.CharField(
        max_length=10,
        help_text='Código del estado'
    )
    estado_descripcion = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Descripción del estado'
    )
    fecha_cambio = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de cambio de estado'
    )
    nit_relacionado = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='NIT relacionado (si aplica)'
    )
    dv_relacionado = models.CharField(
        max_length=1,
        null=True,
        blank=True,
        help_text='DV relacionado'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rut_estados'
        verbose_name = 'Estado RUT'
        verbose_name_plural = 'Estados RUT'
        ordering = ['-fecha_cambio']
    
    def __str__(self):
        return f"{self.rut.nit}-{self.rut.dv} - Estado: {self.estado_codigo}"

```

---

## 📋 Campos Extraíbles del PDF

### Extracción Automática (OCR/PDF Parsing):

1. **Campos de Texto Estructurado**:
   - NIT y DV
   - Razón Social, Nombre Comercial, Sigla
   - Dirección completa
   - Teléfono, Email
   - Fechas (constitución, registro, etc.)
   - Códigos CIIU

2. **Campos de Tablas**:
   - Actividades económicas (principal, secundaria, otras)
   - Establecimientos (múltiples)
   - Estados del RUT
   - Representantes legales (múltiples)

3. **Campos de Checkboxes/Selección**:
   - Responsabilidades (códigos numéricos)
   - Tipo de contribuyente
   - Naturaleza y formas asociativas

---

## 🔧 Funcionalidades Sugeridas

### 1. **Carga de RUT**:
- Subir PDF del RUT
- Extracción automática con OCR/pdfplumber
- Validación de campos
- Asociación con EmpresaServidor por NIT

### 2. **Consulta DIAN**:
- Integración con API de DIAN (si está disponible)
- Actualización automática de datos
- Validación de NIT y DV

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

## ⚠️ Nota

Este modelo está basado en el PDF real extraído. Todos los campos identificados están incluidos en el modelo.

