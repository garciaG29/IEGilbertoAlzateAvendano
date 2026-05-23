from django import forms

from .models import (
    Horario,
    Materia,
    Profesor,
    PerfilCoordinador,
    Usuario
)


class HorarioForm(forms.ModelForm):

    class Meta:
        model = Horario

        fields = [
            'dia',
            'hora_inicio',
            'hora_fin',
            'materia',
            'profesor',
            'salon'
        ]


class PerfilCoordinadorForm(forms.ModelForm):

    class Meta:
        model = PerfilCoordinador

        fields = [
            'telefono',
            'rol',
            'direccion',
            'biografia',
            'foto',
            'fecha'
        ]

        widgets = {

            'fecha': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),

            'biografia': forms.Textarea(
                attrs={
                    'rows': 5
                }
            )

        }


class UsuarioForm(forms.ModelForm):

    class Meta:
        model = Usuario

        fields = [
            'first_name',
            'email'
        ]