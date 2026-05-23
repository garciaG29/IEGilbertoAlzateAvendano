from django.urls import path
from . import views
from . import views_novedades

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('coordinador/', views.panel_coordinador, name='panel_coordinador'),
    path('coordinador/horarios/', views.panel_horarios, name='panel_horarios'),
    path('coordinador/novedades/', views_novedades.panel_novedades, name='panel_novedades'),
    path('coordinador/novedades/crear/', views_novedades.crear_novedad, name='crear_novedad'),
    path('coordinador/novedades/<int:novedad_id>/eliminar/', views_novedades.eliminar_novedad, name='eliminar_novedad'),
    path('coordinador/import/', views.import_from_file, name='import_from_file'),
    path('profesor/', views.panel_profesor, name='panel_profesor'),
    path('estudiante/', views.panel_estudiante, name='panel_estudiante'),
    path('directivo/', views.panel_directivo, name='panel_directivo'),
    path('import_preview/', views.import_preview, name='import_preview'),
    path(
    'perfil/',
    views.perfil_coordinador,
    name='perfil_coordinador'),
]