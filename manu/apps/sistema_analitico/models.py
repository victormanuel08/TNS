# sistema_analitico/models.py
from django.db import models
from django.contrib.auth.models import User
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField, EncryptedEmailField
from django.utils import timezone
from datetime import timedelta
import json

class Servidor(models.Model):
    TIPO_SERVIDOR_CHOICES = [
        ('FIREBIRD', 'Firebird'),
        ('POSTGRESQL', 'PostgreSQL'),
        ('SQLSERVER', 'SQL Server'),
        ('MYSQL', 'MySQL'),
    ]
    
    nombre = models.CharField(max_length=255)
    host = models.CharField(max_length=255)
    usuario = models.CharField(max_length=255)
    password = EncryptedTextField(max_length=500)
    tipo_servidor = models.CharField(max_length=20, choices=TIPO_SERVIDOR_CHOICES)
    ruta_maestra = models.CharField(max_length=500, null=True, blank=True)
    puerto = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'servidores'
            
    def __str__(self):
        return f"{self.nombre} ({self.tipo_servidor})"

class EmpresaServidor(models.Model):
    servidor = models.ForeignKey(Servidor, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=255)
    nit = models.CharField(max_length=20)
    anio_fiscal = models.IntegerField()
    ruta_base = models.CharField(max_length=500)
    consulta_sql = models.TextField(null=True, blank=True)
    ultima_extraccion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, default='ACTIVO')
    configuracion = models.JSONField(default=dict, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'empresas_servidor'
        unique_together = ['nit', 'anio_fiscal']  # Único globalmente, sin importar servidor
        indexes = [
            models.Index(fields=['nit', 'anio_fiscal']),
            models.Index(fields=['servidor', 'nit']),
        ]
        
    def __str__(self):
        return f"{self.nombre} ({self.nit}) - {self.anio_fiscal} - {self.servidor.nombre}"
        
# Template choices centralizados para evitar duplicación
TEMPLATE_CHOICES = [
    ('retail', 'Retail / Autopago'),  # Pantalla táctil tipo McDonald's
    ('restaurant', 'Restaurante'),     # App de pedidos tipo Makos
    ('pro', 'Profesional'),            # Software contable full
]

class UsuarioEmpresa(models.Model):
    """Relación directa entre usuarios y empresas"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='empresas_permitidas')
    empresa_servidor = models.ForeignKey(EmpresaServidor, on_delete=models.CASCADE, related_name='usuarios_permitidos')
    
    puede_ver = models.BooleanField(default=True)
    puede_editar = models.BooleanField(default=False)
    preferred_template = models.CharField(max_length=20, choices=TEMPLATE_CHOICES, default='pro')
    
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'usuario_empresa_permisos'
        unique_together = ['usuario', 'empresa_servidor']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.empresa_servidor.nombre}"


class UserTenantProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='tenant_profile'
    )
    subdomain = models.CharField(max_length=50, unique=True)
    preferred_template = models.CharField(
        max_length=20,
        choices=TEMPLATE_CHOICES,
        default='pro'
    )

    class Meta:
        db_table = 'user_tenant_profiles'

    def __str__(self):
        return f"{self.user.username} -> {self.subdomain}"

class MovimientoInventario(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('FACTURA_VENTA', 'Factura de Venta'),
        ('REMISION_ENTRADA', 'Remisión de Entrada'),
        ('DEVOLUCION_VENTA', 'Devolución de Venta'),
        ('FACTURA_COMPRA', 'Factura de Compra'),
    ]
    
    empresa_servidor = models.ForeignKey(EmpresaServidor, on_delete=models.CASCADE)
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES)
    fecha = models.DateTimeField()
    fecha_orden_pedido = models.DateTimeField(null=True, blank=True)
    
    # Campos paciente
    paciente = models.CharField(max_length=255, null=True, blank=True)
    cedula_paciente = models.CharField(max_length=20, null=True, blank=True)
    
    # Campos pagador
    pagador = models.CharField(max_length=255, null=True, blank=True)
    nit_pagador = models.CharField(max_length=20, null=True, blank=True)
    
    # Campos clínica
    clinica = models.CharField(max_length=255, null=True, blank=True)
    nit_clinica = models.CharField(max_length=20, null=True, blank=True)
    
    # Campos médico
    medico = models.CharField(max_length=255, null=True, blank=True)
    cedula_medico = models.CharField(max_length=20, null=True, blank=True)
    medico2 = models.CharField(max_length=255, null=True, blank=True)
    cedula_medico2 = models.CharField(max_length=20, null=True, blank=True)
    
    procedimientos = models.TextField(null=True, blank=True)
    
    # Campos ubicación
    codigo_ciudad = models.CharField(max_length=10, null=True, blank=True)
    ciudad = models.CharField(max_length=100)
    
    # Campos bodega
    tipo_bodega = models.CharField(max_length=100)
    codigo_bodega = models.CharField(max_length=10, null=True, blank=True)
    sistema_bodega = models.CharField(max_length=255)
    bodega_contenedor = models.CharField(max_length=255, null=True, blank=True)
    
    # Campos artículo
    articulo_nombre = models.CharField(max_length=255)
    articulo_codigo = models.CharField(max_length=100)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    lote = models.CharField(max_length=100, null=True, blank=True)
    stock_previo = models.IntegerField(null=True, blank=True)
    stock_nuevo = models.IntegerField(null=True, blank=True)
    
    # Campos calculados
    valor_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    lead_time_dias = models.IntegerField(null=True, blank=True)
    es_implante = models.BooleanField(default=False)
    es_instrumental = models.BooleanField(default=False)
    es_equipo_poder = models.BooleanField(default=False)
    
    fecha_extraccion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'movimientos_inventario'
        indexes = [
            # Índices existentes
            models.Index(fields=['empresa_servidor', 'fecha']),
            models.Index(fields=['articulo_codigo', 'tipo_bodega']),
            
            # NUEVOS ÍNDICES para consultas rápidas
            models.Index(fields=['nit_pagador']),
            models.Index(fields=['nit_clinica']),
            models.Index(fields=['cedula_paciente']),
            models.Index(fields=['cedula_medico']),
            models.Index(fields=['cedula_medico2']),
            models.Index(fields=['paciente']),
            models.Index(fields=['pagador']),
            models.Index(fields=['clinica']),
            models.Index(fields=['medico']),
            models.Index(fields=['medico2']),
            models.Index(fields=['ciudad']),
            models.Index(fields=['codigo_ciudad']),
            models.Index(fields=['codigo_bodega']),
            models.Index(fields=['tipo_bodega']),
            models.Index(fields=['articulo_codigo']),
            models.Index(fields=['articulo_nombre']),
            models.Index(fields=['fecha']),  # Índice individual para fecha
        ]
        
        
    def __str__(self):
        return f"{self.tipo_documento} - {self.articulo_codigo} ({self.cantidad})"
        
class APIKeyCliente(models.Model):
    nit = models.CharField(max_length=20, unique=True)
    nombre_cliente = models.CharField(max_length=255)
    api_key = models.CharField(max_length=100, unique=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_caducidad = models.DateTimeField()
    usuario_creador = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,  # Si se elimina el usuario, poner NULL
        null=True,  # Permitir NULL para casos donde no hay usuario (creación automática)
        blank=True,
        related_name='api_keys_creadas'
    )
    empresas_asociadas = models.ManyToManyField('EmpresaServidor', blank=True)
    contador_peticiones = models.IntegerField(default=0)
    fecha_ultima_peticion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'api_keys_clientes'
    
    def __str__(self):
        return f"{self.nombre_cliente} ({self.nit})"
    
    def save(self, *args, **kwargs):
        """
        Guarda el modelo. 
        NOTA: usuario_creador ahora es opcional (null=True) para permitir
        creación automática desde scripts o migraciones. Sin embargo, cuando
        se crea desde la vista (APIKeyManagementViewSet.generar_api_key),
        siempre se establece automáticamente via request.user.
        """
        super().save(*args, **kwargs)
    
    def actualizar_empresas_asociadas(self):
        """
        Actualiza automáticamente las empresas asociadas a este NIT.
        Normaliza el NIT de la API Key y busca empresas con NIT normalizado coincidente.
        Optimizado: intenta búsqueda directa primero, luego normaliza si es necesario.
        """
        import re
        # Normalizar NIT de la API Key (eliminar puntos, guiones, etc.)
        nit_normalizado_api = re.sub(r"\D", "", str(self.nit))
        
        # Intentar búsqueda directa primero (más rápido si el NIT en BD ya está normalizado)
        empresas_directas = EmpresaServidor.objects.filter(nit=nit_normalizado_api)
        if empresas_directas.exists():
            # Si encontramos empresas con búsqueda directa, usarlas
            self.empresas_asociadas.set(empresas_directas)
            return empresas_directas.count()
        
        # Si no funcionó, iterar y normalizar (para casos donde el NIT en BD tiene formato diferente)
        # Solo si hay pocas empresas o es necesario
        todas_empresas = EmpresaServidor.objects.all()
        empresas_coincidentes = []
        
        for empresa in todas_empresas:
            nit_normalizado_empresa = re.sub(r"\D", "", str(empresa.nit))
            if nit_normalizado_api == nit_normalizado_empresa:
                empresas_coincidentes.append(empresa)
        
        # Asignar empresas encontradas
        self.empresas_asociadas.set(empresas_coincidentes)
        return len(empresas_coincidentes)
    
    def incrementar_contador(self):
        """Incrementa el contador y actualiza última petición"""
        self.contador_peticiones += 1
        self.fecha_ultima_peticion = timezone.now()
        self.save()
    
    def esta_expirada(self):
        """Verifica si la API Key ha expirado"""
        return timezone.now() > self.fecha_caducidad
    
    def renovar(self, dias=365):
        """Renueva la API Key por más días"""
        self.fecha_caducidad = timezone.now() + timedelta(days=dias)
        self.save()

class EmpresaPersonalizacion(models.Model):
    """
    Almacena logo y colores personalizados de una empresa.
    Usa NIT normalizado (sin puntos, sin guión y lo que viene después) como clave única.
    """
    nit_normalizado = models.CharField(max_length=20, unique=True, db_index=True)
    logo = models.ImageField(upload_to='empresas/logos/', null=True, blank=True)
    color_primario = models.CharField(max_length=7, default='#DC2626', help_text='Color principal (hex)')
    color_secundario = models.CharField(max_length=7, default='#FBBF24', help_text='Color secundario (hex)')
    color_fondo = models.CharField(max_length=7, default='#f5f5f5', help_text='Color de fondo (hex)')
    modo_teclado = models.CharField(
        max_length=20, 
        default='auto', 
        choices=[
            ('auto', 'Automático (inputmode)'),
            ('virtual', 'Teclado Virtual Personalizado'),
            ('hybrid', 'Híbrido (auto en móvil, virtual en desktop)')
        ],
        help_text='Modo de teclado para el terminal de autopago'
    )
    modo_visualizacion = models.CharField(
        max_length=20,
        default='vertical',
        choices=[
            ('vertical', 'Vertical (Comida) - Grid con scroll vertical'),
            ('horizontal', 'Horizontal (Otros) - Dos filas con scroll lateral')
        ],
        help_text='Modo de visualización de productos en el terminal de autopago'
    )
    # Videos para protector de pantalla
    video_por_defecto = models.FileField(
        upload_to='empresas/videos/', 
        null=True, 
        blank=True,
        help_text='Video por defecto para el protector de pantalla'
    )
    video_lunes = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_martes = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_miercoles = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_jueves = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_viernes = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_sabado = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_domingo = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'empresa_personalizacion'
        verbose_name = 'Personalización de Empresa'
        verbose_name_plural = 'Personalizaciones de Empresas'

    def save(self, *args, **kwargs):
        """Redimensiona el logo al guardar si existe"""
        if self.logo:
            from PIL import Image
            import os
            from django.core.files.uploadedfile import InMemoryUploadedFile
            import io
            from django.core.files.base import ContentFile
            
            # Abrir imagen
            img = Image.open(self.logo)
            
            # Convertir a RGB si es necesario (para PNG con transparencia)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Tamaño máximo para logo: 300x100px (mantener aspect ratio)
            max_width, max_height = 300, 100
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Guardar en memoria
            thumb_io = io.BytesIO()
            img.save(thumb_io, format='JPEG', quality=85, optimize=True)
            thumb_io.seek(0)
            
            # Reemplazar el archivo original
            self.logo.save(
                os.path.basename(self.logo.name),
                ContentFile(thumb_io.read()),
                save=False
            )
            thumb_io.close()
        
        super().save(*args, **kwargs)
    
    def get_video_del_dia(self):
        """Retorna el video correspondiente al día de la semana actual"""
        from datetime import datetime
        dia_semana = datetime.now().weekday()  # 0=Lunes, 6=Domingo
        
        videos_dia = {
            0: self.video_lunes,
            1: self.video_martes,
            2: self.video_miercoles,
            3: self.video_jueves,
            4: self.video_viernes,
            5: self.video_sabado,
            6: self.video_domingo,
        }
        
        return videos_dia.get(dia_semana)
    
    def delete(self, *args, **kwargs):
        """Elimina los archivos asociados cuando se elimina el objeto"""
        import os
        videos = [
            self.video_por_defecto,
            self.video_lunes, self.video_martes, self.video_miercoles,
            self.video_jueves, self.video_viernes, self.video_sabado, self.video_domingo
        ]
        for video in videos:
            if video:
                try:
                    if os.path.exists(video.path):
                        os.remove(video.path)
                except Exception:
                    pass
        if self.logo:
            try:
                if os.path.exists(self.logo.path):
                    os.remove(self.logo.path)
            except Exception:
                pass
        super().delete(*args, **kwargs)
    

class EmpresaDominio(models.Model):
    """
    Relación entre dominio público y empresa TNS.
    Se usa para resolver la empresa (EmpresaServidor) a partir del host del request.
    Al crear, solo se requiere dominio y nit. La empresa_servidor y anio_fiscal se determinan en la primera búsqueda.
    """
    MODO_CHOICES = [
        ('autopago', 'Autopago / Retail'),
        ('ecommerce', 'E-commerce público'),
        ('pro', 'Profesional'),
    ]

    dominio = models.CharField(
        max_length=255,
        unique=True,
        help_text='Dominio completo, por ejemplo: pepito.ecommerce.miapp.com',
    )
    nit = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='NIT de la empresa (sin puntos ni guiones). Se usa para buscar la empresa con año fiscal más reciente.',
    )
    empresa_servidor = models.ForeignKey(
        EmpresaServidor,
        on_delete=models.CASCADE,
        related_name='dominios_publicos',
        null=True,
        blank=True,
        help_text='Empresa servidor asociada a este dominio. Se determina automáticamente en la primera búsqueda.',
    )
    anio_fiscal = models.IntegerField(
        null=True,
        blank=True,
        help_text='Año fiscal más reciente de la empresa. Se actualiza automáticamente si es menor al año actual.',
    )
    modo = models.CharField(
        max_length=20,
        choices=MODO_CHOICES,
        default='ecommerce',
        help_text='Modo principal de este dominio (ecommerce, autopago, pro)',
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'empresa_dominios'
        verbose_name = 'Dominio de Empresa'
        verbose_name_plural = 'Dominios de Empresas'

    def save(self, *args, **kwargs):
        """
        Busca y actualiza automáticamente la empresa_servidor y anio_fiscal:
        1. Si no hay empresa_servidor pero hay nit, busca la empresa con año fiscal más reciente
        2. Si hay empresa_servidor pero anio_fiscal es None o menor al año actual, busca la más reciente
        """
        from django.utils import timezone
        
        # Función auxiliar para normalizar NIT (copiada de views.py)
        def normalize_nit(value: str) -> str:
            """Normaliza NIT: elimina puntos, guiones y espacios, solo dígitos"""
            if not value:
                return ''
            return ''.join(c for c in str(value) if c.isdigit())
        
        # Obtener año actual
        anio_actual = timezone.now().year
        
        # Si no hay empresa_servidor pero hay nit, buscar la empresa
        if not self.empresa_servidor_id and self.nit:
            nit_normalizado = normalize_nit(self.nit)
            if nit_normalizado:
                # Buscar todas las empresas con el mismo NIT normalizado, ordenadas por año fiscal descendente
                empresas_mismo_nit = EmpresaServidor.objects.filter(
                    nit=nit_normalizado
                ).order_by('-anio_fiscal')
                
                if empresas_mismo_nit.exists():
                    empresa_mas_reciente = empresas_mismo_nit.first()
                    self.empresa_servidor = empresa_mas_reciente
                    self.anio_fiscal = empresa_mas_reciente.anio_fiscal
                    print(f"[EmpresaDominio] Dominio '{self.dominio}': empresa encontrada por NIT '{nit_normalizado}': {empresa_mas_reciente.nombre} (Año: {empresa_mas_reciente.anio_fiscal})")
        
        # Si hay empresa_servidor, verificar si necesita actualizar el año fiscal
        if self.empresa_servidor_id:
            # Si anio_fiscal no está establecido o es menor al año actual, buscar el más reciente
            if self.anio_fiscal is None or self.anio_fiscal < anio_actual:
                # Obtener NIT normalizado (del campo nit o de la empresa actual)
                nit_normalizado = None
                if self.nit:
                    nit_normalizado = normalize_nit(self.nit)
                elif self.empresa_servidor.nit:
                    nit_normalizado = normalize_nit(self.empresa_servidor.nit)
                
                if nit_normalizado:
                    # Buscar todas las empresas con el mismo NIT normalizado
                    empresas_mismo_nit = EmpresaServidor.objects.filter(
                        nit=nit_normalizado
                    ).order_by('-anio_fiscal')
                    
                    if empresas_mismo_nit.exists():
                        # Usar el año fiscal más reciente
                        empresa_mas_reciente = empresas_mismo_nit.first()
                        self.anio_fiscal = empresa_mas_reciente.anio_fiscal
                        # Actualizar también la empresa_servidor si es diferente
                        if empresa_mas_reciente.id != self.empresa_servidor_id:
                            empresa_anterior = self.empresa_servidor
                            self.empresa_servidor = empresa_mas_reciente
                            print(f"[EmpresaDominio] Actualizado dominio '{self.dominio}': empresa {empresa_anterior.id} -> {empresa_mas_reciente.id}, año fiscal {self.anio_fiscal}")
                    else:
                        # Si no se encuentra, usar el año fiscal de la empresa actual
                        if self.anio_fiscal is None:
                            self.anio_fiscal = self.empresa_servidor.anio_fiscal
                else:
                    # Si no hay NIT, usar el año fiscal de la empresa actual
                    if self.anio_fiscal is None:
                        self.anio_fiscal = self.empresa_servidor.anio_fiscal
        
        super().save(*args, **kwargs)

    def __str__(self):
        empresa_nombre = self.empresa_servidor.nombre if self.empresa_servidor else 'Sin empresa'
        return f"{self.dominio} -> {empresa_nombre} ({self.modo}, año: {self.anio_fiscal or 'N/A'})"


class EmpresaEcommerceConfig(models.Model):
    """
    Configuración completa del e-commerce para una empresa.
    Incluye colores, textos editables, footer, secciones, etc.
    """
    empresa_servidor = models.OneToOneField(
        EmpresaServidor,
        on_delete=models.CASCADE,
        related_name='ecommerce_config',
        help_text='Empresa servidor asociada'
    )
    
    # Colores y estilos
    color_primario = models.CharField(max_length=7, default='#DC2626', help_text='Color principal (hex)')
    color_secundario = models.CharField(max_length=7, default='#FBBF24', help_text='Color secundario (hex)')
    color_fondo = models.CharField(max_length=7, default='#FFFFFF', help_text='Color de fondo (hex)')
    usar_degradado = models.BooleanField(default=False, help_text='Usar degradado en lugar de color sólido')
    color_degradado_inicio = models.CharField(max_length=7, default='#DC2626', help_text='Color inicio del degradado')
    color_degradado_fin = models.CharField(max_length=7, default='#FBBF24', help_text='Color fin del degradado')
    direccion_degradado = models.CharField(
        max_length=20,
        default='to right',
        choices=[
            ('to right', 'Izquierda a Derecha'),
            ('to bottom', 'Arriba a Abajo'),
            ('to bottom right', 'Diagonal'),
        ],
        help_text='Dirección del degradado'
    )
    
    # Textos editables - Hero Section
    hero_titulo = models.CharField(max_length=200, default='Bienvenido a nuestra tienda en línea', help_text='Título principal')
    hero_subtitulo = models.CharField(max_length=200, default='Pedidos rápidos, sencillos y sin filas', help_text='Subtítulo')
    hero_descripcion = models.TextField(default='Explora nuestro menú y realiza tu pedido en pocos clics.', help_text='Descripción')
    
    # Textos editables - About
    about_titulo = models.CharField(max_length=200, default='Sobre nosotros', help_text='Título de la sección About')
    about_texto = models.TextField(
        default='Somos una marca enfocada en ofrecer la mejor experiencia gastronómica, con ingredientes frescos y recetas únicas.',
        help_text='Texto de la sección About'
    )
    
    # Textos editables - Contact
    contact_titulo = models.CharField(max_length=200, default='Contáctanos', help_text='Título de la sección Contact')
    contact_texto = models.TextField(
        default='Para más información sobre pedidos corporativos, eventos o alianzas, contáctanos a través de nuestros canales oficiales.',
        help_text='Texto de la sección Contact'
    )
    whatsapp_numero = models.CharField(max_length=20, null=True, blank=True, help_text='Número de WhatsApp (solo dígitos)')
    
    # Footer - Texto debajo del logo
    footer_texto_logo = models.TextField(
        null=True,
        blank=True,
        help_text='Texto que aparece debajo del logo en el footer'
    )
    
    # Footer - Links (JSON field para flexibilidad)
    footer_links = models.JSONField(
        default=list,
        help_text='Lista de links del footer. Formato: [{"titulo": "Título", "url": "url", "tipo": "modal|external|file", "icono": "emoji"}]'
    )
    
    # Footer - Secciones (JSON field para organizar links en secciones)
    footer_sections = models.JSONField(
        default=list,
        help_text='Lista de secciones del footer. Formato: [{"titulo": "Título Sección", "links": [{"icono": "emoji", "titulo": "Título", "url": "url", "tipo": "modal|external|file"}]}]'
    )
    
    # Menú - Items del menú principal
    menu_items = models.JSONField(
        default=list,
        help_text='Lista de items del menú. Formato: [{"icono": "emoji", "texto": "Texto", "tipo": "scroll|modal|external|file|content", "destino": "id_seccion|url", "contenido": "html/texto"}]'
    )
    
    # Pasarela de Pago
    # Nota: payment_provider almacena el código de PasarelaPago (ej: 'credibanco')
    # No tiene choices restrictivos porque las pasarelas se gestionan dinámicamente
    payment_provider = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Código de la pasarela de pago (debe coincidir con PasarelaPago.codigo, ej: credibanco)'
    )
    payment_public_key = models.CharField(max_length=255, null=True, blank=True, help_text='Clave pública del proveedor de pago')
    payment_secret_key = models.CharField(max_length=255, null=True, blank=True, help_text='Clave privada (solo backend)')
    payment_access_token = models.CharField(max_length=255, null=True, blank=True, help_text='Access Token (para Mercado Pago)')
    payment_enabled = models.BooleanField(default=False, help_text='Habilitar pagos en línea')
    payment_mode = models.CharField(
        max_length=10,
        default='test',
        choices=[('test', 'Prueba'), ('live', 'Producción')],
        help_text='Modo de la pasarela de pago'
    )
    payment_window_type = models.CharField(
        max_length=20,
        default='new_window',
        choices=[
            ('new_window', 'Nueva Ventana/Pestaña'),
            ('modal', 'Modal (iframe)'),
            ('same_window', 'Misma Ventana')
        ],
        help_text='Cómo abrir la pasarela de pago'
    )
    
    # Logo principal
    logo_url = models.URLField(null=True, blank=True, help_text='URL del logo principal (PNG transparente recomendado)')
    
    # Configuración de secciones (mostrar/ocultar)
    mostrar_menu = models.BooleanField(default=True, help_text='Mostrar menú principal')
    mostrar_hero = models.BooleanField(default=True, help_text='Mostrar sección Hero')
    mostrar_about = models.BooleanField(default=True, help_text='Mostrar sección About')
    mostrar_contact = models.BooleanField(default=True, help_text='Mostrar sección Contact')
    mostrar_footer = models.BooleanField(default=True, help_text='Mostrar footer')
    mostrar_categorias_footer = models.BooleanField(default=True, help_text='Mostrar categorías en el footer')
    
    # Credenciales TNS para inserción de facturas
    usuario_tns = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Usuario TNS para inserción de facturas (ej: ADMIN)'
    )
    password_tns = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Contraseña del usuario TNS (encriptada)'
    )
    
    # Estilo general (similar a autopago)
    estilo_tema = models.CharField(
        max_length=20,
        default='balanceado',
        choices=[
            ('balanceado', 'Balanceado (Recomendado)'),
            ('moderno', 'Moderno'),
            ('minimalista', 'Minimalista'),
            ('colorido', 'Colorido'),
            ('elegante', 'Elegante'),
        ],
        help_text='Tema de estilo general'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'empresa_ecommerce_config'
        verbose_name = 'Configuración E-commerce'
        verbose_name_plural = 'Configuraciones E-commerce'
    
    def __str__(self):
        return f"E-commerce Config: {self.empresa_servidor.nombre}"


class PasarelaPago(models.Model):
    """
    Modelo para gestionar las pasarelas de pago disponibles.
    Por ahora solo tiene Credibanco, pero puede extenderse.
    """
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text='Código único de la pasarela (ej: credibanco)'
    )
    nombre = models.CharField(
        max_length=100,
        help_text='Nombre descriptivo de la pasarela (ej: Credibanco)'
    )
    activa = models.BooleanField(
        default=True,
        help_text='Si la pasarela está activa y disponible'
    )
    configuracion = models.JSONField(
        default=dict,
        blank=True,
        help_text='Configuración específica de la pasarela (URLs, endpoints, campos adicionales). Formato JSON.'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pasarela_pago'
        verbose_name = 'Pasarela de Pago'
        verbose_name_plural = 'Pasarelas de Pago'
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class TransaccionPago(models.Model):
    """
    Modelo para guardar todas las transacciones de pago del e-commerce.
    Se crea cuando se inicia un pago y se actualiza cuando Credibanco responde.
    """
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('PROCESANDO', 'Procesando'),
        ('EXITOSA', 'Exitosa'),
        ('FALLIDA', 'Fallida'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    empresa_servidor = models.ForeignKey(
        EmpresaServidor,
        on_delete=models.CASCADE,
        related_name='transacciones_pago',
        help_text='Empresa a la que pertenece esta transacción'
    )
    pasarela_pago = models.ForeignKey(
        PasarelaPago,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transacciones',
        help_text='Pasarela de pago utilizada'
    )
    order_number = models.CharField(
        max_length=100,
        unique=True,
        help_text='Número de orden único (correlativo)'
    )
    order_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='ID de orden de la pasarela (ej: orderId de Credibanco)'
    )
    monto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Monto de la transacción'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE',
        help_text='Estado actual de la transacción'
    )
    datos_cliente = models.JSONField(
        default=dict,
        help_text='Datos del cliente (nombres, apellidos, email, teléfono, dirección, etc.)'
    )
    datos_respuesta = models.JSONField(
        null=True,
        blank=True,
        help_text='Respuesta completa de la pasarela de pago'
    )
    approval_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Código de autorización de la pasarela'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Mensaje de error si la transacción falló'
    )
    factura_tns_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID de la factura creada en TNS (si la transacción fue exitosa)'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transaccion_pago'
        verbose_name = 'Transacción de Pago'
        verbose_name_plural = 'Transacciones de Pago'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['order_id']),
            models.Index(fields=['estado']),
            models.Index(fields=['empresa_servidor', 'fecha_creacion']),
        ]
    
    def __str__(self):
        return f"Transacción {self.order_number} - {self.estado} - ${self.monto}"


class GrupoMaterialImagen(models.Model):
    """
    Almacena imágenes para grupos de materiales (categorías).
    Usa NIT normalizado y código de grupo (GM_CODIGO) como clave única.
    """
    nit_normalizado = models.CharField(max_length=20, db_index=True)
    gm_codigo = models.CharField(max_length=50, db_index=True)
    imagen = models.ImageField(upload_to='grupos/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'grupo_material_imagen'
        unique_together = [['nit_normalizado', 'gm_codigo']]
        indexes = [
            models.Index(fields=['nit_normalizado', 'gm_codigo']),
        ]
        verbose_name = 'Imagen de Grupo de Material'
        verbose_name_plural = 'Imágenes de Grupos de Material'
    
    def save(self, *args, **kwargs):
        """Redimensiona la imagen al guardar si existe, preservando transparencia PNG"""
        import os
        # Eliminar imagen anterior si existe y se está reemplazando
        if self.pk:  # Si el objeto ya existe en la BD
            try:
                old_instance = GrupoMaterialImagen.objects.get(pk=self.pk)
                if old_instance.imagen and old_instance.imagen != self.imagen:
                    # Si hay una imagen anterior diferente, eliminarla
                    if os.path.exists(old_instance.imagen.path):
                        os.remove(old_instance.imagen.path)
            except GrupoMaterialImagen.DoesNotExist:
                pass
        
        if self.imagen:
            from PIL import Image
            from django.core.files.uploadedfile import InMemoryUploadedFile
            import io
            from django.core.files.base import ContentFile
            
            # Abrir imagen
            img = Image.open(self.imagen)
            original_format = img.format
            has_transparency = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
            
            # Si tiene transparencia, mantenerla; si no, convertir a RGB
            if has_transparency:
                # Mantener transparencia: convertir P a RGBA si es necesario
                if img.mode == 'P':
                    img = img.convert('RGBA')
                # No convertir a RGB, mantener RGBA o LA
            else:
                # Sin transparencia: convertir a RGB para optimizar
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
            
            # Tamaño para categorías: 200x200px (cuadrado, mantener aspect ratio)
            max_size = 200
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Guardar en memoria
            thumb_io = io.BytesIO()
            
            # Si tiene transparencia, guardar como PNG; si no, como JPEG
            if has_transparency:
                img.save(thumb_io, format='PNG', optimize=True)
            else:
                img.save(thumb_io, format='JPEG', quality=85, optimize=True)
            
            thumb_io.seek(0)
            
            # Reemplazar el archivo original
            self.imagen.save(
                os.path.basename(self.imagen.name),
                ContentFile(thumb_io.read()),
                save=False
            )
            thumb_io.close()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Elimina la imagen del sistema de archivos cuando se elimina el objeto"""
        import os
        if self.imagen:
            if os.path.exists(self.imagen.path):
                os.remove(self.imagen.path)
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"Grupo {self.gm_codigo} - NIT: {self.nit_normalizado}"


class MaterialImagen(models.Model):
    """
    Almacena imágenes, características y PDF para materiales (artículos) individuales.
    Usa NIT normalizado y código de material (CODIGO) como clave única.
    """
    nit_normalizado = models.CharField(max_length=20, db_index=True)
    codigo_material = models.CharField(max_length=50, db_index=True)
    imagen = models.ImageField(upload_to='materiales/', null=True, blank=True)
    caracteristicas = models.TextField(null=True, blank=True, help_text='Características del producto')
    pdf = models.FileField(upload_to='materiales/pdfs/', null=True, blank=True, help_text='PDF con información del producto')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'material_imagen'
        unique_together = [['nit_normalizado', 'codigo_material']]
        indexes = [
            models.Index(fields=['nit_normalizado', 'codigo_material']),
        ]
        verbose_name = 'Imagen de Material'
        verbose_name_plural = 'Imágenes de Materiales'
    
    def save(self, *args, **kwargs):
        """Redimensiona la imagen al guardar si existe, preservando transparencia PNG"""
        import os
        # Eliminar imagen anterior si existe y se está reemplazando
        if self.pk:  # Si el objeto ya existe en la BD
            try:
                old_instance = MaterialImagen.objects.get(pk=self.pk)
                if old_instance.imagen and old_instance.imagen != self.imagen:
                    # Si hay una imagen anterior diferente, eliminarla
                    if os.path.exists(old_instance.imagen.path):
                        os.remove(old_instance.imagen.path)
            except MaterialImagen.DoesNotExist:
                pass
        
        if self.imagen:
            from PIL import Image
            from django.core.files.uploadedfile import InMemoryUploadedFile
            import io
            from django.core.files.base import ContentFile
            
            # Abrir imagen
            img = Image.open(self.imagen)
            original_format = img.format
            has_transparency = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
            
            # Si tiene transparencia, mantenerla; si no, convertir a RGB
            if has_transparency:
                # Mantener transparencia: convertir P a RGBA si es necesario
                if img.mode == 'P':
                    img = img.convert('RGBA')
                # No convertir a RGB, mantener RGBA o LA
            else:
                # Sin transparencia: convertir a RGB para optimizar
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
            
            # Tamaño para productos: 400x400px (cuadrado, mantener aspect ratio)
            max_size = 400
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Guardar en memoria
            thumb_io = io.BytesIO()
            
            # Si tiene transparencia, guardar como PNG; si no, como JPEG
            if has_transparency:
                img.save(thumb_io, format='PNG', optimize=True)
            else:
                img.save(thumb_io, format='JPEG', quality=85, optimize=True)
            
            thumb_io.seek(0)
            
            # Reemplazar el archivo original
            self.imagen.save(
                os.path.basename(self.imagen.name),
                ContentFile(thumb_io.read()),
                save=False
            )
            thumb_io.close()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Elimina la imagen del sistema de archivos cuando se elimina el objeto"""
        import os
        if self.imagen:
            if os.path.exists(self.imagen.path):
                os.remove(self.imagen.path)
        if self.pdf:
            if os.path.exists(self.pdf.path):
                os.remove(self.pdf.path)
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"Material {self.codigo_material} - NIT: {self.nit_normalizado}"


class CajaAutopago(models.Model):
    """
    Configuración de cajas autopago para cada empresa.
    Relaciona empresa + usuario TNS + IP del datafono local.
    Permite que cada empresa tenga múltiples cajas, cada una con su propio datafono.
    """
    empresa_servidor = models.ForeignKey(
        EmpresaServidor, 
        on_delete=models.CASCADE, 
        related_name='cajas_autopago',
        help_text='Empresa a la que pertenece esta caja'
    )
    usuario_tns = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Usuario TNS que configuró esta caja (puede ser ADMIN o usuario específico)'
    )
    nombre = models.CharField(
        max_length=100,
        help_text='Nombre identificador de la caja (ej: "Caja Principal", "Caja 1", etc.)'
    )
    ip_datafono = models.CharField(
        max_length=45,  # IPv6 puede tener hasta 45 caracteres
        help_text='IP del servidor local donde está el datafono (vía WireGuard, ej: 10.8.0.5)'
    )
    puerto_datafono = models.IntegerField(
        default=8080,
        help_text='Puerto del servidor local del datafono'
    )
    activa = models.BooleanField(
        default=True,
        help_text='Si la caja está activa y disponible para procesar pagos'
    )
    modo_mock = models.BooleanField(
        default=False,
        help_text='Si está en True, simula respuestas sin usar el datafono físico'
    )
    probabilidad_exito = models.FloatField(
        default=0.8,
        help_text='Probabilidad de éxito en modo mock (0.0 a 1.0). 0.8 = 80%% de éxito'
    )
    modo_mock_dian = models.BooleanField(
        default=True,
        help_text='Si está en True, simula el envío a DIAN sin procesar realmente (espera 4 segundos y retorna exitoso)'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    usuario_creador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cajas_autopago_creadas',
        help_text='Usuario de Django que creó esta configuración'
    )
    
    class Meta:
        db_table = 'caja_autopago'
        verbose_name = 'Caja Autopago'
        verbose_name_plural = 'Cajas Autopago'
        indexes = [
            models.Index(fields=['empresa_servidor', 'activa']),
            models.Index(fields=['ip_datafono', 'puerto_datafono']),
        ]
        # Permitir múltiples cajas por empresa, pero nombres únicos por empresa
        unique_together = [['empresa_servidor', 'nombre']]
    
    def __str__(self):
        return f"{self.nombre} - {self.empresa_servidor.nombre} ({self.ip_datafono}:{self.puerto_datafono})"


class NotaRapida(models.Model):
    """
    Modelo para opciones rápidas de notas que se pueden asociar a categorías de productos.
    Ejemplo: "SIN CEBOLLA", "SIN SALSA DE TOMATE", "AL CLIMA", etc.
    """
    texto = models.CharField(max_length=100, help_text="Texto de la nota rápida (ej: SIN CEBOLLA)")
    categorias = models.JSONField(
        default=list,
        help_text="Lista de códigos de categorías (GM_CODIGO) a las que se asocia esta nota. Vacío = todas las categorías"
    )
    activo = models.BooleanField(default=True)
    orden = models.IntegerField(default=0, help_text="Orden de visualización")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notas_rapidas'
        ordering = ['orden', 'texto']
        verbose_name = 'Nota Rápida'
        verbose_name_plural = 'Notas Rápidas'
    
    def __str__(self):
        return self.texto

class ConfiguracionSistema(models.Model):
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descripcion = models.TextField(null=True, blank=True)
    tipo = models.CharField(max_length=50, default='TEXTO')
    
    class Meta:
        db_table = 'configuracion_sistema'
        
        
    def __str__(self):
        return f"{self.clave} ({self.tipo})"


class VpnConfig(models.Model):
    """
    Configuración de túnel VPN WireGuard.
    Almacena la información de cada cliente/PC que se conecta vía VPN.
    """
    nombre = models.CharField(max_length=255, help_text="Nombre descriptivo del cliente/PC")
    ip_address = models.CharField(max_length=50, null=True, blank=True, help_text="IP asignada en la red VPN (ej: 10.8.0.5)")
    public_key = models.TextField(null=True, blank=True, help_text="Clave pública WireGuard del cliente")
    private_key = EncryptedTextField(max_length=500, null=True, blank=True, help_text="Clave privada WireGuard del cliente (encriptada)")
    config_file_path = models.CharField(max_length=500, null=True, blank=True, help_text="Ruta del archivo .conf generado")
    activo = models.BooleanField(default=True, help_text="Si el túnel está activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    notas = models.TextField(null=True, blank=True, help_text="Notas adicionales sobre esta configuración")
    
    class Meta:
        db_table = 'vpn_configs'
        verbose_name = 'Configuración VPN'
        verbose_name_plural = 'Configuraciones VPN'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.nombre} ({self.ip_address or 'Sin IP'})"
        
def user_has_empresa_permission(self, empresa_servidor, permiso='ver'):
    if self.is_superuser:
        return True
    
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(
            usuario=self, 
            empresa_servidor=empresa_servidor
        )
        return getattr(usuario_empresa, f'puede_{permiso}', False)
    except UsuarioEmpresa.DoesNotExist:
        return False

def user_empresas_permitidas(self):
    if self.is_superuser:
        return EmpresaServidor.objects.all()
    return EmpresaServidor.objects.filter(
        usuarios_permitidos__usuario=self,
        usuarios_permitidos__puede_ver=True
    ).distinct()
    
# Extender User para API Keys
def user_puede_gestionar_api_keys(self):
    if self.is_superuser:
        return True
    # Usuarios con permisos de edición en al menos una empresa pueden gestionar API Keys
    return UsuarioEmpresa.objects.filter(usuario=self, puede_editar=True).exists()

# Extender el modelo User
User.add_to_class('puede_gestionar_api_keys', user_puede_gestionar_api_keys)
User.add_to_class('has_empresa_permission', user_has_empresa_permission)
User.add_to_class('empresas_permitidas', user_empresas_permitidas)
