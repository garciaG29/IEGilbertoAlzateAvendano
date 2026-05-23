import pandas as pd

from django.core.management.base import BaseCommand

from usuarios.models import (
    Horario,
    Materia,
    Profesor,
    Usuario
)

from datetime import date, datetime


class Command(BaseCommand):

    help = 'Importar horarios desde Excel'

    def handle(self, *args, **kwargs):

        archivo = 'HORARIO.xlsx'

        df = pd.read_excel(archivo)

        for _, row in df.iterrows():

            # =========================
            # DATOS
            # =========================

            grupo = str(row['Grupo']).strip()

            dia = str(row['Día']).strip().lower()

            materia_nombre = str(
                row['Materia']
            ).strip()

            profesor_nombre = str(
                row['Docente']
            ).strip()

            salon = str(
                row['Aula ']
            ).strip()

            # =========================
            # USUARIO
            # =========================

            username = profesor_nombre.lower().replace(' ', '_')

            usuario, created = Usuario.objects.get_or_create(

                cedula=username,

                defaults={

                    'username': username,

                    'rol': 'profesor',

                    'email': f'{username}@colegio.com'

                }
            )

            if created:

                usuario.set_password('123456')

                usuario.save()

            # =========================
            # PROFESOR
            # =========================

            profesor, _ = Profesor.objects.get_or_create(

                usuario=usuario,

                defaults={

                    'telefono': '0000000000',

                    'especialidad': materia_nombre,

                    'fecha_ingreso': date.today()

                }
            )

            # =========================
            # MATERIA
            # =========================

            materia, _ = Materia.objects.get_or_create(

                nombre=materia_nombre,

                defaults={

                    'codigo': materia_nombre[:5].upper(),

                    'profesor': profesor

                }
            )

            # =========================
            # HORAS
            # =========================

            hora = str(row['Hora Exacta'])

            partes = hora.split('-')

            hora_inicio = datetime.strptime(

                partes[0].strip(),

                '%H:%M'

            ).time()

            hora_fin = datetime.strptime(

                partes[1].strip(),

                '%H:%M'

            ).time()

            # =========================
            # HORARIO
            # =========================

            Horario.objects.create(

                dia=dia,

                grupo=grupo,

                hora_inicio=hora_inicio,

                hora_fin=hora_fin,

                materia=materia,

                profesor=profesor,

                salon=salon,

                es_base=True
            )

        self.stdout.write(

            self.style.SUCCESS(

                'Horarios importados correctamente'

            )

        )
        