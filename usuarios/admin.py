from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Profesor, Materia, Horario, Novedad


class UsuarioAdmin(UserAdmin):
    model = Usuario

    list_display = ('cedula', 'username', 'email', 'rol', 'is_staff')

    fieldsets = UserAdmin.fieldsets + (
        ('Información adicional', {
            'fields': ('cedula', 'rol')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información adicional', {
            'fields': ('cedula', 'rol')
        }),
    )


class HorarioAdmin(admin.ModelAdmin):
    list_display = ('grupo', 'dia', 'hora_inicio', 'hora_fin', 'materia', 'profesor', 'salon', 'es_base')
    list_filter = ('grupo', 'dia', 'es_base', 'materia', 'profesor')
    search_fields = ('grupo', 'materia__nombre', 'profesor__usuario__username')
    ordering = ('grupo', 'dia', 'hora_inicio')


class NovedadAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'grupo', 'dia', 'hora_inicio', 'tipo_novedad', 'activa')
    list_filter = ('fecha', 'grupo', 'tipo_novedad', 'activa', 'dia')
    search_fields = ('grupo', 'materia_original__nombre', 'profesor_original__usuario__username')
    readonly_fields = ('fecha', 'grupo', 'dia', 'hora_inicio', 'hora_fin', 'materia_original', 'profesor_original', 'salon_original')
    ordering = ('-fecha', 'grupo')
    
    fieldsets = (
        ('Información de la novedad', {
            'fields': ('fecha', 'tipo_novedad', 'activa', 'observacion')
        }),
        ('Horario afectado', {
            'fields': ('grupo', 'dia', 'hora_inicio', 'hora_fin', 'materia_original', 'profesor_original', 'salon_original')
        }),
        ('Nuevas asignaciones (si aplica)', {
            'fields': ('materia_nueva', 'profesor_nuevo', 'salon_nuevo'),
            'classes': ('collapse',)
        }),
    )


admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Profesor)
admin.site.register(Materia)
admin.site.register(Horario, HorarioAdmin)
admin.site.register(Novedad, NovedadAdmin)