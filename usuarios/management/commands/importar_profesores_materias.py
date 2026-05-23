from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from usuarios.models import Profesor, Materia
import csv
import re


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip())


class Command(BaseCommand):
    help = 'Importa profesores y materias desde un CSV de dos columnas: materia,profesor'

    def add_arguments(self, parser):
        parser.add_argument('file', nargs='?', help='Ruta al archivo CSV o TXT. Si se omite, lee stdin.')

    def handle(self, *args, **options):
        path = options.get('file')
        lines = []
        if path:
            with open(path, encoding='utf-8') as f:
                lines = f.readlines()
        else:
            import sys
            lines = sys.stdin.read().splitlines()

        User = get_user_model()
        created_users = 0
        created_profes = 0
        created_mats = 0
        updated_mats = 0

        today = timezone.now().date()

        for raw in lines:
            if not raw or raw.strip().startswith('#'):
                continue
            # Split by tab or multiple spaces or comma
            parts = re.split(r'[\t,]+|\s{2,}|\s/\s|\s/|/\s|/', raw)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) < 2:
                # try splitting by whitespace into two
                parts = raw.split(None, 1)
                if len(parts) < 2:
                        self.stdout.write(f'Skipping invalid line: {raw}')

            # Find or create user by username (case-insensitive)
            user = User.objects.filter(username__iexact=profesor_name).first()
            if not user:
                # generate a cedula unique
                base = re.sub(r'[^a-z0-9]', '', profesor_name.lower())[:10]
                cedula = f'import_{base}'
                i = 1
                while User.objects.filter(cedula=cedula).exists():
                    cedula = f'import_{base}_{i}'
                    i += 1

                user = User(cedula=cedula, username=profesor_name, email=f'{base}@example.com', rol='profesor')
                user.set_unusable_password()
                user.save()
                created_users += 1

            profesor = Profesor.objects.filter(usuario=user).first()
            if not profesor:
                profesor = Profesor(usuario=user, telefono='', especialidad='', fecha_ingreso=today, estado=True)
                profesor.save()
                created_profes += 1

            # Create or update materia
            materia = Materia.objects.filter(nombre__iexact=materia_name).first()
            if not materia:
                materia = Materia.objects.create(nombre=materia_name, codigo='', profesor=profesor)
                created_mats += 1
            else:
                if materia.profesor != profesor:
                    materia.profesor = profesor
                    materia.save()
                    updated_mats += 1

        self.stdout.write(f'Usuarios creados: {created_users}')
        self.stdout.write(f'Profesores creados: {created_profes}')
        self.stdout.write(f'Materias creadas: {created_mats}')
        self.stdout.write(f'Materias actualizadas: {updated_mats}')
