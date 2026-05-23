# GAA Colegio

Proyecto Django para gestionar horarios y usuarios.

Pasos rápidos para ejecutar localmente:

1. Crear y activar entorno virtual:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS / Linux
```

2. Instalar dependencias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Migrar y crear superusuario:

```bash
python manage.py migrate
python manage.py createsuperuser
```

4. Importar profesoras y materias (usando el archivo `data/profesores_materias.txt` ya incluido):

```bash
python manage.py importar_profesores_materias data/profesores_materias.txt
```

El comando crea `Usuario` (con `rol='profesor'`) y `Profesor` si no existen, y crea o reasigna `Materia` al profesor.

Nota: el comando genera usuarios con `cedula` tipo `import_<nombre>` y contraseña inutilizable. Ajusta los datos manualmente si quieres credenciales reales.
