from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class Usuario(AbstractUser):

    ROLES = (
        ('coordinador', 'Coordinador'),
        ('profesor', 'Profesor'),
        ('estudiante', 'Estudiante'),
        ('directivo', 'Directivo'),
    )

    cedula = models.CharField(max_length=20, unique=True)

    rol = models.CharField(max_length=20, choices=ROLES)

    USERNAME_FIELD = 'cedula'

    REQUIRED_FIELDS = ['username', 'email']

    def __str__(self):
        return self.username


class Profesor(models.Model):

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE
    )

    telefono = models.CharField(max_length=20)

    especialidad = models.CharField(max_length=100)

    estado = models.BooleanField(default=True)

    fecha_ingreso = models.DateField()

    def __str__(self):
        return self.usuario.username


class Materia(models.Model):

    nombre = models.CharField(max_length=100)

    codigo = models.CharField(max_length=20)

    descripcion = models.TextField(blank=True, null=True)

    profesor = models.ForeignKey(
        Profesor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.nombre


class Horario(models.Model):

    DIAS = [
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
    ]

    dia = models.CharField(max_length=15, choices=DIAS)

    grupo = models.CharField(max_length=20)

    hora_inicio = models.TimeField()

    hora_fin = models.TimeField()

    materia = models.ForeignKey(
        Materia,
        on_delete=models.CASCADE
    )

    profesor = models.ForeignKey(
        Profesor,
        on_delete=models.CASCADE
    )

    fecha_actualizacion = models.DateTimeField(
    auto_now=True,
    null=True,
    blank=True
    )
    
    salon = models.CharField(max_length=20)

    es_base = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.grupo} - {self.materia}"
    
    


class Novedad(models.Model):

    TIPOS_NOVEDAD = [
        ('cambio_clase', 'Cambio de Clase'),
        ('cambio_profesor', 'Cambio de Profesor'),
        ('cambio_salon', 'Cambio de Salón'),
        ('no_asiste', 'No Asiste/Grupo Ausente'),
        ('suspendida', 'Clase Suspendida'),
        ('otra', 'Otra Novedad'),
    ]

    fecha = models.DateField()

    grupo = models.CharField(max_length=20)

    dia = models.CharField(max_length=15, choices=Horario.DIAS)

    hora_inicio = models.TimeField()

    hora_fin = models.TimeField()

    tipo_novedad = models.CharField(max_length=50, choices=TIPOS_NOVEDAD)

    materia_original = models.ForeignKey(
        Materia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='novedades_original'
    )

    profesor_original = models.ForeignKey(
        Profesor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='novedades_original'
    )

    salon_original = models.CharField(max_length=20, blank=True, null=True)

    # Para las nuevas asignaciones en caso de cambio
    materia_nueva = models.ForeignKey(
        Materia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='novedades_nueva'
    )

    profesor_nuevo = models.ForeignKey(
        Profesor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='novedades_nueva'
    )

    salon_nuevo = models.CharField(max_length=20, blank=True, null=True)

    observacion = models.TextField(blank=True, null=True)

    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.grupo} - {self.get_tipo_novedad_display()} - {self.fecha}"

    class Meta:
        ordering = ['-fecha', 'grupo']
        verbose_name_plural = 'Novedades'


class PerfilCoordinador(models.Model):

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE
    )

    telefono = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    rol = models.CharField(
        max_length=100,
        default='Coordinador'
    )

    direccion = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    biografia = models.TextField(
        blank=True,
        null=True
    )

    foto = models.ImageField(
        upload_to='perfiles/',
        blank=True,
        null=True
    )

    fecha = models.DateField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.usuario.username