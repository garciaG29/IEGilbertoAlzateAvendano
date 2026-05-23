"""
Vista para el panel de novedades de horarios.
Permite crear, editar y visualizar novedades de los horarios.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime, time
from .models import Horario, Novedad, Materia, Profesor, Profesor
from .views import get_fixed_professors, FIXED_PROFESSORS


def get_fixed_professors_local():
    """Wrapper para obtener profesores fijos"""
    return get_fixed_professors()


@login_required
@user_passes_test(lambda u: u.is_staff)
def panel_novedades(request):
    """Panel para ver y crear novedades de horarios"""
    
    default_groups = [
        '6-1', '6-2',
        '8-1', '8-2',
        '9-1', '9-2', '9-3', '9-4', '9-5', '9-6',
        '10-1', '10-2', '10-3', '10-4', '10-5', '10-6', '10-7',
        '11-1', '11-2', '11-3', '11-4', '11-5', '11-6', '11-7',
    ]
    
    selected_group = request.GET.get('group', default_groups[0])
    selected_date = request.GET.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        fecha_selected = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        fecha_selected = datetime.now().date()
    
    # Obtener novedades activas para el grupo y fecha seleccionados
    novedades = Novedad.objects.filter(
        grupo=selected_group,
        fecha=fecha_selected,
        activa=True
    ).select_related('materia_original', 'profesor_original', 'materia_nueva', 'profesor_nuevo').order_by('hora_inicio')
    
    # Obtener el horario base para el grupo
    horario_base = Horario.objects.filter(
        grupo=selected_group,
        es_base=True
    ).select_related('materia', 'profesor__usuario').order_by('dia', 'hora_inicio')
    
    # Agrupar novedades por franja horaria
    dia_choices = [('lunes', 'Lunes'), ('martes', 'Martes'), ('miercoles', 'Miércoles'), ('jueves', 'Jueves'), ('viernes', 'Viernes')]
    
    # Construcción de datos para la vista
    contexto = {
        'groups': default_groups,
        'selected_group': selected_group,
        'selected_date': selected_date,
        'fecha_selected': fecha_selected,
        'novedades': novedades,
        'horario_base': horario_base,
        'dia_choices': dia_choices,
        'tipo_novedad_choices': Novedad.TIPOS_NOVEDAD,
        'subjects': Materia.objects.all().order_by('nombre'),
        'teachers': get_fixed_professors_local(),
    }
    
    return render(request, 'usuarios/novedades.html', contexto)


@login_required
@user_passes_test(lambda u: u.is_staff)
def crear_novedad(request):
    """Crear una nueva novedad para un horario"""
    
    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        grupo = request.POST.get('grupo')
        dia = request.POST.get('dia')
        hora_inicio = request.POST.get('hora_inicio')
        hora_fin = request.POST.get('hora_fin')
        tipo_novedad = request.POST.get('tipo_novedad')
        observacion = request.POST.get('observacion', '')
        
        # Campos para cambios
        materia_original_id = request.POST.get('materia_original')
        profesor_original_id = request.POST.get('profesor_original')
        materia_nueva_id = request.POST.get('materia_nueva')
        profesor_nuevo_id = request.POST.get('profesor_nuevo')
        salon_nuevo = request.POST.get('salon_nuevo', '')
        
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
            hora_fin_obj = datetime.strptime(hora_fin, '%H:%M').time()
            
            # Obtener objetos relacionados
            materia_original = Materia.objects.get(id=materia_original_id) if materia_original_id else None
            profesor_original = Profesor.objects.get(id=profesor_original_id) if profesor_original_id else None
            materia_nueva = Materia.objects.get(id=materia_nueva_id) if materia_nueva_id else None
            profesor_nuevo = Profesor.objects.get(id=profesor_nuevo_id) if profesor_nuevo_id else None
            
            # Obtener el horario original
            horario_original = Horario.objects.filter(
                grupo=grupo,
                dia=dia,
                hora_inicio=hora_inicio_obj,
                hora_fin=hora_fin_obj,
                es_base=True
            ).first()
            
            if not horario_original and tipo_novedad != 'no_asiste':
                messages.error(request, 'No se encontró el horario base para esta franja.')
                return redirect('panel_novedades')
            
            # Crear o actualizar la novedad
            novedad, created = Novedad.objects.update_or_create(
                fecha=fecha_obj,
                grupo=grupo,
                dia=dia,
                hora_inicio=hora_inicio_obj,
                hora_fin=hora_fin_obj,
                tipo_novedad=tipo_novedad,
                defaults={
                    'materia_original': materia_original or (horario_original.materia if horario_original else None),
                    'profesor_original': profesor_original or (horario_original.profesor if horario_original else None),
                    'salon_original': horario_original.salon if horario_original else '',
                    'materia_nueva': materia_nueva,
                    'profesor_nuevo': profesor_nuevo,
                    'salon_nuevo': salon_nuevo,
                    'observacion': observacion,
                    'activa': True,
                }
            )
            
            if created:
                messages.success(request, 'Novedad creada exitosamente.')
            else:
                messages.success(request, 'Novedad actualizada exitosamente.')
                
        except (ValueError, Materia.DoesNotExist, Profesor.DoesNotExist) as e:
            messages.error(request, f'Error al crear la novedad: {str(e)}')
        
        return redirect(f'panel_novedades?group={grupo}&date={fecha}')
    
    return redirect('panel_novedades')


@login_required
@user_passes_test(lambda u: u.is_staff)
def eliminar_novedad(request, novedad_id):
    """Desactivar una novedad"""
    
    novedad = get_object_or_404(Novedad, id=novedad_id)
    novedad.activa = False
    novedad.save()
    
    messages.success(request, 'Novedad desactivada exitosamente.')
    
    return redirect(f'panel_novedades?group={novedad.grupo}&date={novedad.fecha}')

