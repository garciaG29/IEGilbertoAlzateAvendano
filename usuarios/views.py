from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Horario, Profesor, Materia, Usuario, Novedad
from django.conf import settings
from pathlib import Path
import re
import unicodedata
from datetime import time, date, datetime
from django.contrib.auth.decorators import user_passes_test
from django.core.management import call_command
import io
from .models import PerfilCoordinador
from .forms import PerfilCoordinadorForm, UsuarioForm
from datetime import datetime

# Helper: split a raw line into (materia_chunk, profesor_chunk)
def split_pair(raw: str):
    # Prefer tab-separated
    if '\t' in raw:
        parts = raw.split('\t', 1)
        return parts[0].strip(), parts[1].strip()

    # Otherwise try splitting by two or more spaces
    m = re.split(r"\s{2,}", raw, maxsplit=1)
    if len(m) >= 2:
        return m[0].strip(), m[1].strip()

    # Fallback: split at the first whitespace-separated token boundary
    parts = raw.split(None, 1)
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()

    return raw.strip(), ''


def normalize_materia_name(value):
    if value is None:
        return ''

    raw = str(value).strip()
    if raw in {'MAT. / ING.', 'REL. / MAT.', 'TEC. / ING.'}:
        return raw

    cleaned = raw.split('/', 1)[0]
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r'\.$', '', cleaned)
    return cleaned


BASE_SCHEDULES = {
    '6-1': [
        ['TEC. (MANEDY) Aula 9', 'C. NAT. (YESICA) Aula 9', 'SOC. (RUTH E) Aula 4', 'ETI (RUTH E) Aula 10', 'C. NAT. (YESICA) Aula 9'],
        ['TEC. (MANEDY) Aula 9', 'C. NAT. (YESICA) Aula 9', 'SOC. (RUTH E) Aula 4', 'ING. (RUBEN) Aula 10', 'C. NAT. (YESICA) Aula 9'],
        ['ESP. (NEVARDO) Aula 7', 'ED.FIS (RUTH V) Cancha 1', 'ART. (MANEDY) Aula 10', 'ING. (RUBEN) Aula 10', 'MAT. (WILMER) Aula 24'],
        ['ESP. (NEVARDO) Aula 7', 'ED.FIS (RUTH V) Cancha 1', 'ART. (MANEDY) Aula 10', 'TEC. (MANEDY) Aula 5', 'MAT. (WILMER) Aula 24'],
        ['MAT. (WILMER) Aula 4', 'ING. (RUBEN) Aula 7', 'REL. (LAURA) Aula 5', 'TEC. (MANEDY) Aula 5', 'SOC. (RUTH E.) Aula 5'],
        ['MAT. (WILMER) Aula 4', 'ING. (RUBEN) Aula 7', 'REL. (LAURA) Aula 5', 'ESP. (NEVARDO) Aula 7', 'SOC. (RUTH E.) Aula 5'],
    ],
    '6-2': [
        ['ESP. (NEVARDO) Aula 10', 'ESP. (NEVARDO) Aula 4', 'ING. (RUBEN) Aula 7', 'MAT. (DANIEL) Aula 5', 'MAT. (DANIEL) Aula 10'],
        ['ESP. (NEVARDO) Aula 10', 'ESP. (NEVARDO) Aula 4', 'ING. (RUBEN) Aula 7', 'MAT. (DANIEL) Aula 5', 'MAT. (DANIEL) Aula 10'],
        ['SOC. (RUTH E) Aula 4', 'ART. (MANEDY) Aula 5', 'C. NAT. (YESICA) Aula 9', 'REL. (LAURA) Aula 7', 'ING. (RUBEN) Aula 5'],
        ['SOC. (RUTH E) Aula 4', 'ART. (MANEDY) Aula 5', 'C. NAT. (YESICA) Aula 9', 'REL. (LAURA) Aula 7', 'SOC. (RUTH E) Lab'],
        ['C. NAT. (YESICA) Aula 24', 'ETI (RUTH E) Aula 9', 'MAT. (DANIEL) Lab', 'TEC. (MANEDY) Aula 10', 'ED.FIS (RUTH V) Cancha 1'],
        ['C. NAT. (YESICA) Aula 24', 'ETI (RUTH E) Aula 9', 'REL. (LAURA) Aula 10', 'TEC. (MANEDY) Aula 10', 'ED.FIS (RUTH V) Cancha 1'],
    ],
    '8-1': [
        ['SOC. (RUTH E) Aula 5', 'MAT. (JORGE O) Aula 3', 'ESP. (NEVARDO) Aula 3', 'TEC. (MANEDY) Aula 5', 'ETI (RUTH E.) Aula 1'],
        ['SOC. (RUTH E) Aula 5', 'MAT. (JORGE O) Aula 3', 'ESP. (NEVARDO) Aula 3', 'MAT. (JORGE O) Aula 9', 'ETI (RUTH E.) Aula 1'],
        ['REL. (YESICA) Aula 9', 'ING. (RUBEN) Aula 7', 'ED.FIS (RUTH V) Cancha 3', 'MAT. (JORGE O) Aula 9', 'C. NAT. (YESICA) Aula 5'],
        ['REL. (YESICA) Aula 9', 'ING. (RUBEN) Aula 7', 'ED.FIS (RUTH V) Cancha 3', 'ING. (RUBEN) Aula 3', 'C. NAT. (YESICA) Aula 5'],
        ['TEC. (MANEDY) Aula 10', 'C. NAT. (YESICA) Aula 9', 'SOC. (RUTH E.) Aula 4', 'ING. (RUBEN) Aula 3', 'ESP. (NEVARDO) Aula 9'],
        ['TEC. (MANEDY) Aula 10', 'C. NAT. (YESICA) Aula 9', 'SOC. (RUTH E.) Aula 4', 'ART. (YAN POL) Aula 2', 'ESP. (NEVARDO) Aula 9'],
    ],
    '8-2': [
        ['MAT. (JORGE O) Aula 3', 'ETI (YESICA) Aula 5', 'REL. (YESICA) Aula 3', 'C. NAT. (YESICA) Aula 4', 'MAT. (JORGE O) Aula 10'],
        ['MAT. (JORGE O) Aula 3', 'ETI (YESICA) Aula 5', 'MAT. (JORGE O) Aula 2', 'C. NAT. (YESICA) Aula 4', 'MAT. (JORGE O) Aula 10'],
        ['ING. (VILMA) Aula 2', 'ESP. (ALEXANDRA) Aula 4', 'MAT. (JORGE O) Aula 2', 'ESP. (NEVARDO) Aula 1', 'ED.FIS (RUTH V) Cancha 3'],
        ['ING. (VILMA) Aula 2', 'ESP. (ALEXANDRA) Aula 4', 'SOC. (ALEXANDRA) Aula 1', 'ESP. (NEVARDO) Aula 1', 'ED.FIS (RUTH V) Cancha 3'],
        ['TEC. (MANEDY) Aula 12', 'SOC. (RUTH E) Aula 10', 'ART. (YAN POL) Aula 9', 'ING. (VILMA) Aula 9', 'TEC. (MANEDY) Aula 12'],
        ['TEC. (MANEDY) Aula 12', 'SOC. (RUTH E) Aula 10', 'ART. (YAN POL) Aula 9', 'ING. (VILMA) Aula 9', 'TEC. (MANEDY) Aula 12'],
    ],
    '9-1': [
        ['ING. (VILMA) Aula 12', 'MAT. (JORGE O) Aula 1', 'QUÍ. (DIANA) Aula 1', 'FIL. (NEVARDO) Aula 1', 'MAT. (JORGE O) Aula 3'],
        ['ING. (VILMA) Aula 12', 'MAT. (JORGE O) Aula 1', 'QUÍ. (DIANA) Aula 1', 'FIL. (NEVARDO) Aula 1', 'MAT. (JORGE O) Aula 3'],
        ['C. NAT. (YESICA) Aula 4', 'ESP. (ALEXANDRA) Aula 1', 'ART. (YAN POL) Aula 4', 'C. NAT. (YESICA) Aula 1', 'ING. (VILMA) Aula 4'],
        ['C. NAT. (YESICA) Aula 4', 'ESP. (ALEXANDRA) Aula 1', 'SOC. (FREDY) Aula 1', 'C. NAT. (YESICA) Aula 1', 'ING. (VILMA) Aula 4'],
        ['TEC. (MANEDY) Aula 11', 'SOC. (FREDY) Aula 2', 'ED.FIS (RUTH V) Cancha 2', 'ESP. (ALEXANDRA) Aula 1', 'SOC. (FREDY) Aula 1'],
        ['TEC. (MANEDY) Aula 11', 'SOC. (FREDY) Aula 2', 'ED.FIS (RUTH V) Cancha 2', 'ESP. (ALEXANDRA) Aula 1', 'REL. (LAURA) Aula 1'],
    ],
    '9-2': [
        ['C. NAT. (YESICA) Aula 4', 'SOC. (FREDY) Aula 2', 'MAT. (JORGE O) Aula 2', 'QUÍ. (DIANA) Aula 2', 'SOC. (FREDY) Aula 2'],
        ['C. NAT. (YESICA) Aula 4', 'SOC. (FREDY) Aula 2', 'MAT. (JORGE O) Aula 2', 'QUÍ. (DIANA) Aula 2', 'SOC. (FREDY) Aula 2'],
        ['ING. (VILMA) Aula 12', 'MAT. (JORGE O) Aula 1', 'FIL. (NEVARDO) Aula 2', 'ING. (VILMA) Aula 2', 'ESP. (ALEXANDRA) Aula 2'],
        ['ING. (VILMA) Aula 12', 'MAT. (JORGE O) Aula 1', 'FIL. (NEVARDO) Aula 2', 'ING. (VILMA) Aula 2', 'ESP. (ALEXANDRA) Aula 2'],
        ['ED.FIS (RUTH V) Cancha 2', 'ESP. (ALEXANDRA) Aula 3', 'ART. (YAN POL) Aula 2', 'C. NAT. (YESICA) Aula 2', 'TEC. (MANEDY) Aula 11'],
        ['ED.FIS (RUTH V) Cancha 2', 'ESP. (ALEXANDRA) Aula 3', 'REL. (LAURA) Aula 2', 'C. NAT. (YESICA) Aula 2', 'TEC. (MANEDY) Aula 11'],
    ],
    '9-3': [
        ['MAT. (WILMER) Aula 4', 'ESP. (NEVARDO) Aula 5', 'MAT. (WILMER) Aula 10', 'SOC. (RUTH E) Aula 4', 'ART. (MANEDY) Aula 10'],
        ['MAT. (WILMER) Aula 4', 'ESP. (NEVARDO) Aula 5', 'MAT. (WILMER) Aula 10', 'ESP. (NEVARDO) Aula 10', 'ART. (MANEDY) Aula 10'],
        ['TEC. (MANEDY) Aula 5', 'ING. (RUBEN) Aula 10', 'ESP. (NEVARDO) Aula 5', 'SOC. (RUTH E) Aula 4', 'ED.FIS (RUTH V) Cancha 1'],
        ['TEC. (MANEDY) Aula 5', 'ING. (RUBEN) Aula 10', 'REL. (LAURA) Aula 7', 'C. NAT. (YESICA) Aula 9', 'ED.FIS (RUTH V) Cancha 1'],
        ['C. NAT. (YESICA) Aula 9', 'MAT. (WILMER) Aula 24', 'ING. (RUBEN) Aula 7', 'C. NAT. (YESICA) Aula 9', 'ETI (RUTH E) Aula 10'],
        ['C. NAT. (YESICA) Aula 9', 'MAT. (WILMER) Aula 24', 'ING. (RUBEN) Aula 7', 'QUÍ. (DIANA) Aula 1', 'SOC. (RUTH E) Aula 4'],
    ],
    '9-4': [
        ['MAT. (WILMER) Aula 24', 'MAT. (WILMER) Aula 24', 'ART. (MANEDY) Aula 10', 'C. NAT. (YESICA) Aula 9', 'TEC. (MANEDY) Aula 5'],
        ['MAT. (WILMER) Aula 24', 'MAT. (WILMER) Aula 24', 'ART. (MANEDY) Aula 10', 'C. NAT. (YESICA) Aula 9', 'TEC. (MANEDY) Aula 5'],
        ['C. NAT. (YESICA) Aula 9', 'SOC. (RUTH E) Aula 5', 'ING. (RUBEN) Aula 7', 'ESP. (NEVARDO) Aula 7', 'SOC. (RUTH E) Aula 4'],
        ['C. NAT. (YESICA) Aula 9', 'SOC. (RUTH E) Aula 5', 'ING. (RUBEN) Aula 7', 'ESP. (NEVARDO) Aula 7', 'SOC. (RUTH E) Aula 4'],
        ['ESP. (NEVARDO) Aula 10', 'ED.FIS (RUTH V) Cancha 1', 'REL. (LAURA) Aula 10', 'ING. (RUBEN) Aula 10', 'MAT. (WILMER) Aula 24'],
        ['ESP. (NEVARDO) Aula 10', 'ED.FIS (RUTH V) Cancha 1', 'ETI (RUTH E) Aula 9', 'ING. (RUBEN) Aula 10', 'QUÍ. (DIANA) Aula 1'],
    ],
    '9-5': [
        ['ART. (YAN POL) Aula 1', 'ING. (RUBEN) Aula 3', 'SOC. (RUTH E) Aula 5', 'MAT. (DANIEL) Aula 5', 'ED.FIS (RUTH V) Cancha 1'],
        ['ART. (YAN POL) Aula 1', 'ING. (RUBEN) Aula 3', 'SOC. (RUTH E) Aula 5', 'MAT. (DANIEL) Aula 5', 'ED.FIS (RUTH V) Cancha 1'],
        ['MAT. (DANIEL) Aula 5', 'TEC. (MANEDY) Aula 12', 'MAT. (DANIEL) Aula 10', 'QUÍ. (DIANA) Aula 1', 'C. NAT. (YESICA) Aula 9'],
        ['MAT. (DANIEL) Aula 5', 'TEC. (MANEDY) Aula 12', 'MAT. (DANIEL) Aula 10', 'ESP. (NEVARDO) Aula 4', 'C. NAT. (YESICA) Aula 9'],
        ['SOC. (RUTH E) Aula 4', 'ESP. (NEVARDO) Aula 4', 'C. NAT. (YESICA) Aula 9', 'REL. (LAURA) Aula 7', 'ING. (RUBEN) Aula 5'],
        ['ETI (RUTH E) Aula 9', 'ESP. (NEVARDO) Aula 4', 'C. NAT. (YESICA) Aula 9', 'REL. (LAURA) Aula 7', 'ING. (RUBEN) Aula 5'],
    ],
    '9-6': [
        ['MAT. (DANIEL) Aula 5', 'ING. (RUBEN) Aula 10', 'MAT. (DANIEL) Lab', 'SOC. (RUTH E) Aula 4', 'ESP. (NEVARDO) Aula 10'],
        ['MAT. (DANIEL) Aula 5', 'ING. (RUBEN) Aula 10', 'MAT. (DANIEL) Lab', 'SOC. (RUTH E) Aula 4', 'ESP. (NEVARDO) Aula 10'],
        ['ESP. (NEVARDO) Aula 10', 'C. NAT. (YESICA) Aula 9', 'ED.FIS (RUTH V) Cancha 1', 'TEC. (MANEDY) Aula 10', 'QUÍ. (DIANA) Aula 1'],
        ['ETI (RUTH E) Aula 9', 'C. NAT. (YESICA) Aula 9', 'ED.FIS (RUTH V) Cancha 1', 'TEC. (MANEDY) Aula 10', 'ING. (RUBEN) Aula 5'],
        ['ART. (MANEDY) Aula 10', 'SOC. (RUTH E) Aula 10', 'C. NAT. (YESICA) Aula 24', 'ING. (RUBEN) Aula 3', 'MAT. (DANIEL) Aula 5'],
        ['ART. (MANEDY) Aula 10', 'SOC. (RUTH E) Aula 10', 'REL. (LAURA) Aula 10', '—', 'MAT. (DANIEL) Aula 5'],
    ],
    '10-1': [
        ['MAT. (JORGE O) Aula 2', 'ESP. (ALEXANDRA) Aula 3', 'ECO. (ARMANDO) Aula 3', 'FIL. (NEVARDO) Aula 3', 'CÍV. (ARMANDO) Aula 3'],
        ['MAT. (JORGE O) Aula 2', 'ESP. (ALEXANDRA) Aula 3', 'ECO. (ARMANDO) Aula 3', 'FIL. (NEVARDO) Aula 3', 'ING. (VILMA) Aula 3'],
        ['ESP. (ALEXANDRA) Aula 3', 'QUÍ. (DIANA) Aula 3', 'MAT. (JORGE O) Aula 3', 'MAT. (JORGE O) Aula 3', 'ING. (VILMA) Aula 3'],
        ['ESP. (ALEXANDRA) Aula 3', 'QUÍ. (DIANA) Aula 3', 'MAT. (JORGE O) Aula 3', 'MAT. (JORGE O) Aula 3', 'FÍS. (MIGUEL) Aula 3'],
        ['SOC. (FREDY) Aula 1', 'TR. GRADO (MIGUEL) Aula 3', 'FÍS. (MIGUEL) Aula 3', 'QUÍ. (DIANA) Aula 3', 'REL. (LAURA) Aula 3'],
        ['SOC. (FREDY) Aula 1', 'TR. GRADO (MIGUEL) Aula 3', 'FÍS. (MIGUEL) Aula 3', 'QUÍ. (DIANA) Aula 3', 'ED.FIS (GABRIEL) Cancha 2'],
        ['—', '—', '—', '—', 'ED.FIS (GABRIEL) Cancha 2'],
    ],
    '10-2': [
        ['QUÍ. (DIANA) Aula 11', 'FÍS. (MIGUEL) Aula 11', 'ESP. (ALEXANDRA) Aula 11', 'CÍV. (ARMANDO) Aula 11', 'ESP. (ALEXANDRA) Aula 11'],
        ['QUÍ. (DIANA) Aula 11', 'FÍS. (MIGUEL) Aula 11', 'ESP. (ALEXANDRA) Aula 11', 'ING. (VILMA) Aula 11', 'ESP. (ALEXANDRA) Aula 11'],
        ['MAT. (JORGE O) Aula 11', 'ECO. (ARMANDO) Aula 11', 'FIL. (NEVARDO) Aula 11', 'ING. (VILMA) Aula 11', 'REL. (LAURA) Aula 11'],
        ['MAT. (JORGE O) Aula 11', 'ECO. (ARMANDO) Aula 11', 'FIL. (NEVARDO) Aula 11', 'TR. GRADO (MIGUEL) Aula 11', 'SOC. (FREDY) Aula 11'],
        ['QUÍ. (DIANA) Aula 11', 'MAT. (JORGE O) Aula 11', 'MAT. (JORGE O) Aula 11', 'TR. GRADO (MIGUEL) Aula 11', 'SOC. (FREDY) Aula 11'],
        ['QUÍ. (DIANA) Aula 11', 'MAT. (JORGE O) Aula 11', 'MAT. (JORGE O) Aula 11', 'FÍS. (MIGUEL) Aula 11', 'ED.FIS (GABRIEL) Cancha 3'],
        ['—', '—', '—', '—', 'ED.FIS (GABRIEL) Cancha 3'],
    ],
    '10-3': [
        ['FIL. (NEVARDO) Aula 2', 'ESP. (ALEXANDRA) Aula 2', 'ECO. (ARMANDO) Aula 2', 'ESP. (ALEXANDRA) Aula 2', 'QUÍ. (DIANA) Aula 2'],
        ['FIL. (NEVARDO) Aula 2', 'ESP. (ALEXANDRA) Aula 2', 'ECO. (ARMANDO) Aula 2', 'MAT. (JORGE O) Aula 4', 'QUÍ. (DIANA) Aula 2'],
        ['SOC. (FREDY) Aula 2', 'MAT. (JORGE O) Aula 1', 'QUÍ. (DIANA) Aula 2', 'MAT. (JORGE O) Aula 4', 'ESP. (ALEXANDRA) Aula 2'],
        ['SOC. (FREDY) Aula 2', 'MAT. (JORGE O) Aula 1', 'QUÍ. (DIANA) Aula 2', 'ING. (VILMA) Aula 2', 'ESP. (ALEXANDRA) Aula 2'],
        ['ING. (VILMA) Aula 12', 'FÍS. (MIGUEL) Aula 2', 'MAT. (JORGE O) Aula 2', 'TR. GRADO (MIGUEL) Aula 2', 'CÍV. (ARMANDO) Aula 2'],
        ['ING. (VILMA) Aula 12', 'FÍS. (MIGUEL) Aula 2', 'MAT. (JORGE O) Aula 2', 'TR. GRADO (MIGUEL) Aula 2', 'REL. (LAURA) Aula 2'],
        ['—', '—', 'FÍS. (MIGUEL) Aula 2', '—', 'ED.FIS (GABRIEL) Cancha 3'],
        ['—', '—', '—', '—', 'ED.FIS (GABRIEL) Cancha 3'],
    ],
    '10-4': [
        ['MAT. (JORGE O) Aula 4', 'FIL. (NEVARDO) Aula 4', 'ESP. (ALEXANDRA) Aula 4', 'ING. (VILMA) Aula 4', 'MAT. (JORGE O) Aula 4'],
        ['MAT. (JORGE O) Aula 4', 'FIL. (NEVARDO) Aula 4', 'ESP. (ALEXANDRA) Aula 4', 'ING. (VILMA) Aula 4', 'MAT. (JORGE O) Aula 4'],
        ['QUÍ. (DIANA) Aula 4', 'ECO. (ARMANDO) Aula 4', 'MAT. (JORGE O) Aula 4', 'CÍV. (ARMANDO) Aula 4', 'QUÍ. (DIANA) Aula 4'],
        ['QUÍ. (DIANA) Aula 4', 'ECO. (ARMANDO) Aula 4', 'ED.FIS (GABRIEL) Cancha 2', 'ESP. (ALEXANDRA) Aula 4', 'QUÍ. (DIANA) Aula 4'],
        ['TR. GRADO (MIGUEL) Aula 4', 'ING. (VILMA) Aula 4', 'ED.FIS (GABRIEL) Cancha 2', 'FÍS. (MIGUEL) Aula 4', 'SOC. (FREDY) Aula 4'],
        ['TR. GRADO (MIGUEL) Aula 4', 'REL. (LAURA) Aula 5', 'ESP. (ALEXANDRA) Aula 4', 'FÍS. (MIGUEL) Aula 4', 'SOC. (FREDY) Aula 4'],
        ['—', '—', '—', '—', 'FÍS. (MIGUEL) Aula 4'],
    ],
    '10-5': [
        ['ESP. (ALEXANDRA) Aula 5', 'MAT. (WILMER) Aula 5', 'MAT. (WILMER) Aula 5', 'QUÍ. (DIANA) Aula 5', 'MAT. (WILMER) Aula 5'],
        ['ESP. (ALEXANDRA) Aula 5', 'MAT. (WILMER) Aula 5', 'MAT. (WILMER) Aula 5', 'QUÍ. (DIANA) Aula 5', 'MAT. (WILMER) Aula 5'],
        ['FIL. (NEVARDO) Aula 5', 'ESP. (ALEXANDRA) Aula 5', 'ED.FIS (GABRIEL) Cancha 2', 'ECO. (ARMANDO) Aula 5', 'QUÍ. (DIANA) Aula 5'],
        ['FIL. (NEVARDO) Aula 5', 'ESP. (ALEXANDRA) Aula 5', 'ED.FIS (GABRIEL) Cancha 2', 'ECO. (ARMANDO) Aula 5', 'QUÍ. (DIANA) Aula 5'],
        ['TR. GRADO (MIGUEL) Aula 5', 'ING. (VILMA) Aula 5', 'SOC. (FREDY) Aula 5', 'ING. (VILMA) Aula 5', 'FÍS. (MIGUEL) Aula 5'],
        ['TR. GRADO (MIGUEL) Aula 5', 'ING. (VILMA) Aula 5', 'SOC. (FREDY) Aula 5', 'CÍV. (ARMANDO) Aula 5', 'FÍS. (MIGUEL) Aula 5'],
        ['—', '—', '—', 'REL. (LAURA) Aula 5', 'FÍS. (MIGUEL) Aula 5'],
    ],
    '10-6': [
        ['ECO. (ARMANDO) Aula 1', 'ESP. (ALEXANDRA) Aula 1', 'ING. (VILMA) Aula 1', 'MAT. (JORGE O) Aula 1', 'FIL. (NEVARDO) Aula 1'],
        ['ECO. (ARMANDO) Aula 1', 'ESP. (ALEXANDRA) Aula 1', 'ING. (VILMA) Aula 1', 'MAT. (JORGE O) Aula 1', 'FIL. (NEVARDO) Aula 1'],
        ['QUÍ. (DIANA) Aula 1', 'MAT. (JORGE O) Aula 1', 'ESP. (ALEXANDRA) Aula 1', 'FÍS. (MIGUEL) Aula 1', 'CÍV. (ARMANDO) Aula 1'],
        ['QUÍ. (DIANA) Aula 1', 'MAT. (JORGE O) Aula 1', 'ESP. (ALEXANDRA) Aula 1', 'FÍS. (MIGUEL) Aula 1', 'REL. (LAURA) Aula 1'],
        ['SOC. (FREDY) Aula 1', 'QUÍ. (DIANA) Aula 1', 'TR. GRADO (MIGUEL) Aula 1', 'ED.FIS (GABRIEL) Cancha 3', 'ING. (VILMA) Aula 1'],
        ['SOC. (FREDY) Aula 1', 'QUÍ. (DIANA) Aula 1', 'TR. GRADO (MIGUEL) Aula 1', 'ED.FIS (GABRIEL) Cancha 3', 'MAT. (JORGE O) Aula 1'],
        ['—', '—', '—', 'FÍS. (MIGUEL) Aula 1', '—'],
    ],
    '10-7': [
        ['ESP. (ALEXANDRA) Aula 10', 'FIL. (NEVARDO) Aula 10', 'MAT. (JORGE O) Aula 9', 'TR. GRADO (MIGUEL) Aula 10', 'ECO. (ARMANDO) Aula 10'],
        ['ESP. (ALEXANDRA) Aula 10', 'FIL. (NEVARDO) Aula 10', 'MAT. (JORGE O) Aula 9', 'TR. GRADO (MIGUEL) Aula 10', 'ECO. (ARMANDO) Aula 10'],
        ['MAT. (JORGE O) Aula 9', 'ING. (VILMA) Aula 12', 'SOC. (FREDY) Aula 10', 'QUÍ. (DIANA) Aula 10', 'FÍS. (MIGUEL) Aula 10'],
        ['MAT. (JORGE O) Aula 9', 'ING. (VILMA) Aula 12', 'SOC. (FREDY) Aula 10', 'QUÍ. (DIANA) Aula 10', 'FÍS. (MIGUEL) Aula 10'],
        ['QUÍ. (DIANA) Aula 10', 'ED.FIS (GABRIEL) Cancha 3', 'ESP. (ALEXANDRA) Aula 10', 'ING. (VILMA) Aula 10', 'CÍV. (ARMANDO) Aula 10'],
        ['QUÍ. (DIANA) Aula 10', 'ED.FIS (GABRIEL) Cancha 3', 'ESP. (ALEXANDRA) Aula 10', 'REL. (LAURA) Aula 10', 'MAT. (JORGE O) Aula 10'],
        ['—', '—', 'TEC. (RUTH V) Aula 8', '—', 'ECON. POL. (ALEJANDRO) Aula 20'],
        ['—', '—', '—', '—', 'SOC. (ARMANDO) Aula 8'],
    ],
    '11-1': [
        ['SOC. (FREDY) Aula 1', 'FIL. (NEVARDO) Aula 12', 'TR. GRADO (MIGUEL) Aula 12', 'FÍS. (MIGUEL) Aula 12', 'QUÍ. (DIANA) Aula 12'],
        ['SOC. (FREDY) Aula 1', 'FIL. (NEVARDO) Aula 12', 'TR. GRADO (MIGUEL) Aula 12', 'FÍS. (MIGUEL) Aula 12', 'QUÍ. (DIANA) Aula 12'],
        ['QUÍ. (DIANA) Aula 12', 'MAT. (JORGE O) Aula 12', 'ING. (VILMA) Aula 12', 'ESP. (ALEXANDRA) Aula 12', 'ECO. (ARMANDO) Aula 12'],
        ['QUÍ. (DIANA) Aula 12', 'MAT. (JORGE O) Aula 12', 'ING. (VILMA) Aula 12', 'ESP. (ALEXANDRA) Aula 12', 'ECO. (ARMANDO) Aula 12'],
        ['ESP. (ALEXANDRA) Aula 12', 'ING. (VILMA) Aula 12', 'MAT. (JORGE O) Aula 12', 'CÍV. (ARMANDO) Aula 12', 'ED.FIS (GABRIEL) Cancha 3'],
        ['ESP. (ALEXANDRA) Aula 12', '—', 'MAT. (JORGE O) Aula 12', 'REL. (LAURA) Aula 12', 'ED.FIS (GABRIEL) Cancha 3'],
        ['FÍS. (MIGUEL) Aula 12', '—', '—', '—', '—'],
    ],
    '11-2': [
        ['ECO. (ARMANDO) Aula 12', 'FIL. (NEVARDO) Aula 12', 'ESP. (ALEXANDRA) Aula 12', 'MAT. (JORGE O) Aula 12', 'SOC. (FREDY) Aula 12'],
        ['ECO. (ARMANDO) Aula 12', 'FIL. (NEVARDO) Aula 12', 'ESP. (ALEXANDRA) Aula 12', 'MAT. (JORGE O) Aula 12', 'SOC. (FREDY) Aula 12'],
        ['ING. (VILMA) Aula 12', 'ESP. (ALEXANDRA) Aula 12', 'MAT. (JORGE O) Aula 12', 'QUÍ. (DIANA) Aula 12', 'FÍS. (MIGUEL) Aula 12'],
        ['ING. (VILMA) Aula 12', 'ESP. (ALEXANDRA) Aula 12', 'MAT. (JORGE O) Aula 12', 'QUÍ. (DIANA) Aula 12', 'FÍS. (MIGUEL) Aula 12'],
        ['QUÍ. (DIANA) Aula 12', 'MAT. (JORGE O) Aula 12', 'ING. (VILMA) Aula 12', 'ED.FIS (GABRIEL) Cancha 3', 'CÍV. (ARMANDO) Aula 12'],
        ['QUÍ. (DIANA) Aula 12', '—', 'TR. GRADO (MIGUEL) Aula 12', 'ED.FIS (GABRIEL) Cancha 3', 'REL. (LAURA) Aula 12'],
        ['FÍS. (MIGUEL) Aula 12', '—', 'TR. GRADO (MIGUEL) Aula 12', '—', '—'],
    ],
    '11-3': [
        ['MAT. (JORGE O) Aula 11', 'QUÍ. (DIANA) Aula 11', 'ESP. (ALEXANDRA) Aula 11', 'ECO. (ARMANDO) Aula 11', 'FIL. (NEVARDO) Aula 11'],
        ['MAT. (JORGE O) Aula 11', 'QUÍ. (DIANA) Aula 11', 'ESP. (ALEXANDRA) Aula 11', 'ECO. (ARMANDO) Aula 11', 'FIL. (NEVARDO) Aula 11'],
        ['ESP. (ALEXANDRA) Aula 11', 'FÍS. (MIGUEL) Aula 11', 'QUÍ. (DIANA) Aula 11', 'MAT. (JORGE O) Aula 11', 'ING. (VILMA) Aula 11'],
        ['ESP. (ALEXANDRA) Aula 11', 'FÍS. (MIGUEL) Aula 11', 'QUÍ. (DIANA) Aula 11', 'MAT. (JORGE O) Aula 11', 'ING. (VILMA) Aula 11'],
        ['ING. (VILMA) Aula 11', 'MAT. (JORGE O) Aula 11', 'SOC. (FREDY) Aula 11', 'TR. GRADO (MIGUEL) Aula 11', 'CÍV. (ARMANDO) Aula 11'],
        ['—', '—', 'SOC. (FREDY) Aula 11', 'TR. GRADO (MIGUEL) Aula 11', 'REL. (LAURA) Aula 11'],
        ['FÍS. (MIGUEL) Aula 11', '—', '—', 'ED.FIS (GABRIEL) Cancha 3', '—'],
        ['—', '—', '—', 'ED.FIS (GABRIEL) Cancha 3', '—'],
    ],
    '11-4': [
        ['ESP. (ALEXANDRA) Aula 3', 'QUÍ. (DIANA) Aula 3', 'FIL. (NEVARDO) Aula 3', 'MAT. (JORGE O) Aula 3', 'ECO. (ARMANDO) Aula 3'],
        ['ESP. (ALEXANDRA) Aula 3', 'QUÍ. (DIANA) Aula 3', 'FIL. (NEVARDO) Aula 3', 'MAT. (JORGE O) Aula 3', 'ECO. (ARMANDO) Aula 3'],
        ['TR. GRADO (MIGUEL) Aula 3', 'MAT. (JORGE O) Aula 3', 'ESP. (ALEXANDRA) Aula 3', 'ING. (VILMA) Aula 3', 'FÍS. (MIGUEL) Aula 3'],
        ['TR. GRADO (MIGUEL) Aula 3', 'MAT. (JORGE O) Aula 3', 'ESP. (ALEXANDRA) Aula 3', 'ING. (VILMA) Aula 3', 'FÍS. (MIGUEL) Aula 3'],
        ['MAT. (JORGE O) Aula 3', 'SOC. (FREDY) Aula 1', 'QUÍ. (DIANA) Aula 3', 'ED.FIS (GABRIEL) Cancha 2', 'CÍV. (ARMANDO) Aula 3'],
        ['—', 'SOC. (FREDY) Aula 1', 'QUÍ. (DIANA) Aula 3', 'ED.FIS (GABRIEL) Cancha 2', 'REL. (LAURA) Aula 3'],
        ['FÍS. (MIGUEL) Aula 3', '—', '—', '—', '—'],
    ],
    '11-5': [
        ['SOC. (FREDY) Aula 2', 'MAT. (JORGE O) Aula 1', 'ESP. (ALEXANDRA) Aula 2', 'QUÍ. (DIANA) Aula 2', 'FIL. (NEVARDO) Aula 2'],
        ['SOC. (FREDY) Aula 2', 'MAT. (JORGE O) Aula 1', 'ESP. (ALEXANDRA) Aula 2', 'QUÍ. (DIANA) Aula 2', 'FIL. (NEVARDO) Aula 2'],
        ['QUÍ. (DIANA) Aula 2', 'ESP. (ALEXANDRA) Aula 2', 'FIL. (NEVARDO) Aula 2', 'FÍS. (MIGUEL) Aula 2', 'ECO. (ARMANDO) Aula 2'],
        ['QUÍ. (DIANA) Aula 2', 'ESP. (ALEXANDRA) Aula 2', 'MAT. (JORGE O) Aula 2', 'FÍS. (MIGUEL) Aula 2', 'ECO. (ARMANDO) Aula 2'],
        ['MAT. (JORGE O) Aula 2', 'ING. (VILMA) Aula 2', 'ED.FIS (GABRIEL) Cancha 3', 'MAT. (JORGE O) Aula 2', 'CÍV. (ARMANDO) Aula 2'],
        ['—', 'ING. (VILMA) Aula 2', 'ED.FIS (GABRIEL) Cancha 3', 'REL. (LAURA) Aula 2', 'MAT. (JORGE O) Aula 2'],
        ['FÍS. (MIGUEL) Aula 2', '—', 'TR. GRADO (MIGUEL) Aula 2', '—', '—'],
        ['—', '—', 'TR. GRADO (MIGUEL) Aula 2', '—', '—'],
    ],
    '11-6': [
        ['ESP. (MAURICIO T) Aula 25', 'QUIM. (MAURICIO V) Aula 15', 'SOC. (ARMANDO) Aula 8', 'ECON. POL (ALEJANDRO) Aula 10', 'ING. (RUBEN) Aula 7'],
        ['TEC. (MANEDY) Aula 10', 'ED.FIS Cancha 3', 'MAT. (MAURICIO V) Aula 22', 'ESP. (MAURICIO T) Aula 10', 'FIS. (KEILA) Aula 22'],
        ['MAT. (MAURICIO V) Aula 8', 'Aula 8', 'QUIM. (EDUARD) Aula 25', 'FIS. (KEILA) Aula 22', 'ED.FIS (MIGUEL) Cancha 1'],
        ['LECT. MUS (ANGELA) MUSICA', '—', 'ING. (RUBEN) Aula 7', 'MUSICA (ANGELA) LECT. MUS', 'LOG. PROG (LUIS F) SIST 2'],
        ['FIS. (KEILA) Aula 22', '—', 'ARTIS (MAURICIO V)', '—', 'QUIM. (EDUARD) Aula 15'],
        ['—', '—', 'ART. (BIBIANA) ARTIS', '—', '—'],
    ],
    '11-7': [
        ['FILO. (FREDDY F) Aula 16', 'TEC. (RUTH V) Aula 8', 'MÚSICA (ANGELA) MÚSICA', 'ESP. (MAURICIO T) Aula 25', 'FILO. (FREDDY F) Aula 16'],
        ['MONITOREO (DANIEL) LAB', 'ED.FÍS. (MIGUEL) Cancha 3', 'MAT. (MAURICIO V) Aula 22', 'ESP. (MAURICIO T) Aula 10', 'ETI. (FREDDY F) Aula 16'],
        ['ETI. (KEILA) Aula 22', 'MAT. (MAURICIO V) Aula 8', 'REL. (MANEDY) Aula 10', 'FÍS. (KEILA) Aula 22', 'MAT. (MAURICIO V) Aula 22'],
        ['ING. (RUBEN) Aula 7', '—', 'ESP. (MAURICIO T) Aula 25', 'LECT. MUS. (ANGELA) MÚSICA', 'LECT. MUS. (ANGELA) MÚSICA'],
        ['QUÍM. (EDUARD) Aula 15', '—', 'LAB. MONITOREO (DANIEL) LAB', '—', 'ESP. (MAURICIO T) Aula 22'],
        ['—', '—', 'ART. (BIBIANA) ARTIS', '—', 'ED.FÍS. (MIGUEL) Aula 20'],
        ['—', '—', 'TEC. (RUTH V) Aula 8', '—', 'ECON. POL. (ALEJANDRO) Aula 20'],
        ['—', '—', '—', '—', 'SOC. (ARMANDO) Aula 8'],
    ],
}

FIXED_PROFESSORS = [
    ('Alejandro', 'alejandro'),
    ('Alexandra', 'alexandra'),
    ('Ángela', 'angela'),
    ('Armando', 'armando'),
    ('Bibiana', 'bibiana'),
    ('Cristina', 'cristina'),
    ('Daniel', 'daniel'),
    ('Diana', 'diana'),
    ('Echandia', 'echandia'),
    ('Eduard', 'eduard'),
    ('Freddy F.', 'freddy_f'),
    ('Fredy', 'fredy'),
    ('Gabriel', 'gabriel'),
    ('Henry', 'henry'),
    ('Jonathan', 'jonathan'),
    ('Jonny', 'jonny'),
    ('Jorge H.', 'jorge_h'),
    ('Jorge O.', 'jorge_o'),
    ('JORGE O. / RUBEN', 'jorge_o_ruben'),
    ('YESICA. / JORGE O.', 'yesica_jorge_o'),
    ('MANEDY. / VILMA', 'manedy_vilma'),
    ('Keila', 'keila'),
    ('L. Nodier', 'l._nodier'),
    ('Laura', 'laura'),
    ('Leady', 'leady'),
    ('Luis F.', 'luis_f'),
    ('Manedy', 'manedy'),
    ('María E.', 'maria_e'),
    ('Mauricio T.', 'mauricio_t'),
    ('Mauricio V.', 'mauricio_v'),
    ('Miguel', 'miguel'),
    ('Natalia', 'natalia'),
    ('Nevardo', 'nevardo'),
    ('Paola', 'paola'),
    ('Rubén', 'ruben'),
    ('Ruth E.', 'ruth_e'),
    ('Ruth V.', 'ruth_v'),
    ('Vilma', 'vilma'),
    ('Wilmer', 'wilmer'),
    ('Yan Pol', 'yan_pol'),
    ('Yesica', 'yesica'),
]


def get_fixed_professors(prefetch_materias=False):
    usernames = [username for _, username in FIXED_PROFESSORS]
    qs = Profesor.objects.filter(usuario__username__in=usernames).select_related('usuario')
    if prefetch_materias:
        qs = qs.prefetch_related('materia_set')
    profesores = list(qs)
    profesor_map = {prof.usuario.username: prof for prof in profesores}

    ordered = []
    for display_name, username in FIXED_PROFESSORS:
        prof = profesor_map.get(username)
        if not prof:
            user = Usuario.objects.filter(username__iexact=username).first()
            if not user:
                cedula = f'import_{username}'
                i = 1
                while Usuario.objects.filter(cedula=cedula).exists():
                    cedula = f'import_{username}_{i}'
                    i += 1
                user = Usuario(cedula=cedula, username=username, email=f'{username}@example.com', rol='profesor')
                user.set_unusable_password()
                user.save()
            prof = Profesor.objects.filter(usuario=user).first()
            if not prof:
                prof = Profesor(usuario=user, telefono='', especialidad='', fecha_ingreso=date.today(), estado=True)
                prof.save()
            profesor_map[username] = prof

        prof.display_name = display_name
        ordered.append(prof)

    return ordered

# =========================
# LOGIN
# =========================
def login_view(request):

    if request.method == "POST":

        cedula = request.POST.get("cedula")
        password = request.POST.get("password")

        # Autenticación
        user = authenticate(
            request,
            username=cedula,
            password=password
        )

        if user is not None:

            login(request, user)

            # REDIRECCIÓN AL PERFIL
            return redirect("perfil_coordinador")

        else:
            messages.error(
                request,
                "Credenciales incorrectas"
            )

            return redirect('login')

    return render(request, "login.html")


# =========================
# PERFIL COORDINADOR
# =========================
@login_required
def perfil_coordinador(request):

    perfil, created = PerfilCoordinador.objects.get_or_create(
        usuario=request.user
    )

    if request.method == 'POST':

        # =========================
        # DATOS USUARIO
        # =========================
        request.user.first_name = request.POST.get('first_name')
        request.user.email = request.POST.get('email')
        request.user.save()

        # =========================
        # DATOS PERFIL
        # =========================
        perfil.rol = request.POST.get('rol')
        perfil.telefono = request.POST.get('telefono')
        perfil.direccion = request.POST.get('direccion')
        perfil.biografia = request.POST.get('biografia')

        # =========================
        # FECHA
        # =========================
        fecha = request.POST.get('fecha')

        if fecha:
            perfil.fecha = fecha
        else:
            perfil.fecha = None

        # =========================
        # FOTO
        # =========================
        if 'foto' in request.FILES:
            perfil.foto = request.FILES['foto']

        perfil.save()

        messages.success(
            request,
            'Perfil actualizado correctamente.'
        )

        return redirect('perfil_coordinador')

    contexto = {
        'perfil': perfil
    }

    return render(
        request,
        'usuarios/perfil_coordinador.html',
        contexto
    )

# =========================
# LOGOUT
# =========================
def logout_view(request):
    logout(request)
    return redirect("login")


## =========================
# PANEL COORDINADOR
# =========================
@login_required
def panel_coordinador(request):

    horarios = Horario.objects.all().select_related(
        'profesor__usuario',
        'materia'
    )

    profesores = get_fixed_professors(prefetch_materias=True)

    materias = Materia.objects.all()

    novedades = Novedad.objects.filter(
        activa=True
    ).order_by('-fecha')[:5]

    profesores_activos = Profesor.objects.filter(
        estado=True
    ).count()

    # =========================
    # MATERIAS POR PROFESOR
    # =========================

    fixed_usernames = [username for _, username in FIXED_PROFESSORS]

    horarios_profes = Horario.objects.filter(
        profesor__usuario__username__in=fixed_usernames
    ).select_related('profesor__usuario', 'materia')

    profesor_materias = {prof.id: set() for prof in profesores}

    for horario in horarios_profes:

        if horario.profesor_id in profesor_materias and horario.materia:

            normalized_name = normalize_materia_name(
                horario.materia.nombre
            )

            if normalized_name:
                profesor_materias[horario.profesor_id].add(
                    normalized_name
                )

    for prof in profesores:

        materias_asignadas = sorted(
            profesor_materias.get(prof.id, set())
        )

        if not materias_asignadas:

            materias_asignadas = sorted(
                {
                    normalize_materia_name(m.nombre)
                    for m in prof.materia_set.all()
                    if normalize_materia_name(m.nombre)
                }
            )

        prof.materias_asignadas = materias_asignadas

    # =========================
    # HORARIOS SEMANALES
    # =========================

    dias_semana = [
        'lunes',
        'martes',
        'miercoles',
        'jueves',
        'viernes'
    ]

    conteo_dias = []

    for dia in dias_semana:
        total = Horario.objects.filter(dia=dia).count()
        conteo_dias.append(total)

    # =========================
    # HORARIOS RECIENTES
    # =========================

    horarios_recientes = Horario.objects.all().order_by(
        'hora_inicio'
    )[:6]

    # =========================
    # CONTEXTO
    # =========================

    contexto = {

        "horarios": horarios,

        "profesores": profesores,

        "novedades": novedades,

        "horarios_recientes": horarios_recientes,

        "total_horarios": horarios.count(),

        "total_profesores": len(profesores),

        "total_materias": materias.count(),

        "profesores_activos": profesores_activos,

        "dias_labels": [
            'Lunes',
            'Martes',
            'Miércoles',
            'Jueves',
            'Viernes'
        ],

        "dias_data": conteo_dias,
    }

    return render(
        request,
        "usuarios/coordinador.html",
        contexto
    )


@login_required
def panel_horarios(request):
    default_groups = [
        '6-1', '6-2',
        '8-1', '8-2',
        '9-1', '9-2', '9-3', '9-4', '9-5', '9-6',
        '10-1', '10-2', '10-3', '10-4', '10-5', '10-6', '10-7',
        '11-1', '11-2', '11-3', '11-4', '11-5', '11-6', '11-7',
    ]

    def normalize_group(raw_group):
        if raw_group is None:
            return None
        raw_str = str(raw_group).strip()
        m = re.match(r'^(\d{4})-(\d{2})-(\d{2})(?:\s+\d{2}:\d{2}:\d{2})?$', raw_str)
        if m:
            month = int(m.group(2))
            day = int(m.group(3))
            return f"{month}-{day}"
        return raw_str

    def normalize_name_key(value):
        if not value:
            return ''
        normalized = unicodedata.normalize('NFD', str(value))
        normalized = ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
        normalized = re.sub(r'[^A-Z0-9]', '', normalized.upper())
        return normalized

    def split_subject_room(raw_text):
        if not raw_text:
            return raw_text, ''

        raw_text = raw_text.strip()
        separators = [' Aula ', ' Cancha ', ' LAB', ' MÚSICA', ' MUSICA', ' ARTIS', ' LECT.', ' LAB.']
        for separator in separators:
            index = raw_text.rfind(separator)
            if index != -1:
                return raw_text[:index].strip(), raw_text[index:].strip()

        return raw_text, ''

    def parse_schedule_entry(raw_text, teacher_lookup):
        subject_part, room_part = split_subject_room(raw_text)
        teacher_username = ''
        subject_name = subject_part
        match = re.search(r'\(([^)]+)\)\s*$', subject_part)
        if match:
            teacher_raw = match.group(1).strip()
            subject_name = subject_part[:match.start()].strip()
            teacher_username = teacher_lookup.get(normalize_name_key(teacher_raw), '')
        return subject_name, room_part, teacher_username

    raw_groups = [group for group in Horario.objects.order_by('grupo').values_list('grupo', flat=True).distinct() if group is not None]
    group_mapping = {}
    for raw in raw_groups:
        label = normalize_group(raw)
        if label and label in default_groups and label not in group_mapping:
            group_mapping[label] = raw

    groups = list(default_groups)
    group_mapping.update({label: label for label in default_groups if label not in group_mapping})

    fixed_prof_map = {username: display_name for display_name, username in FIXED_PROFESSORS}
    prof_lookup = {}
    for display_name, username in FIXED_PROFESSORS:
        prof_lookup[normalize_name_key(display_name)] = username
        prof_lookup[normalize_name_key(username)] = username

    materia_lookup = {normalize_name_key(materia.nombre): materia.id for materia in Materia.objects.all()}

    selected_group_label = request.GET.get('group', groups[0])
    if selected_group_label not in groups:
        selected_group_label = groups[0]
    selected_group_raw = group_mapping.get(selected_group_label, selected_group_label)

    day_values = [
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
    ]

    time_slots = [
        {'label': '06:00 - 06:55', 'type': 'normal', 'start': time(6, 0), 'end': time(6, 55)},
        {'label': '06:55 - 07:50', 'type': 'normal', 'start': time(6, 55), 'end': time(7, 50)},
        {'label': '07:50 - 08:45', 'type': 'normal', 'start': time(7, 50), 'end': time(8, 45)},
        {'label': '08:45 - 09:15', 'type': 'break', 'start': time(8, 45), 'end': time(9, 15)},
        {'label': '09:15 - 10:10', 'type': 'normal', 'start': time(9, 15), 'end': time(10, 10)},
        {'label': '10:10 - 11:00', 'type': 'normal', 'start': time(10, 10), 'end': time(11, 0)},
        {'label': '11:00 - 11:50', 'type': 'normal', 'start': time(11, 0), 'end': time(11, 50)},
        {'label': '11:50 - 14:00', 'type': 'break', 'start': time(11, 50), 'end': time(14, 0)},
        {'label': '14:00 - 14:45', 'type': 'normal', 'start': time(14, 0), 'end': time(14, 45)},
        {'label': '15:00 - 15:45', 'type': 'normal', 'start': time(15, 0), 'end': time(15, 45)},
    ]

    slot_lookup = {slot['label']: (slot['start'], slot['end']) for slot in time_slots}

    if request.method == 'POST':
        form_group_label = request.POST.get('group', selected_group_label)
        form_day = request.POST.get('day')
        form_slot = request.POST.get('slot')
        form_materia = request.POST.get('materia')
        form_profesor = request.POST.get('profesor')
        form_salon = request.POST.get('salon', '').strip()
        action = request.POST.get('action')

        form_group_raw = group_mapping.get(form_group_label, form_group_label)

        if form_day and form_slot and form_group_label in groups and form_slot in slot_lookup:
            start_time, end_time = slot_lookup[form_slot]
            if action == 'clear':
                Horario.objects.filter(
                    grupo=form_group_raw,
                    dia=form_day,
                    hora_inicio=start_time,
                    hora_fin=end_time,
                ).delete()
                messages.success(request, 'Horario eliminado correctamente.')
                return redirect(f"{request.path}?group={form_group_label}")

            materia = Materia.objects.filter(pk=form_materia).first() if form_materia else None
            profesor = Profesor.objects.filter(pk=form_profesor).first() if form_profesor else None

            if not materia or not profesor:
                messages.error(request, 'Seleccione materia y profesor válidos para guardar el horario.')
                return redirect(f"{request.path}?group={form_group_label}")

            Horario.objects.update_or_create(
                grupo=form_group_raw,
                dia=form_day,
                hora_inicio=start_time,
                hora_fin=end_time,
                defaults={
                    'materia': materia,
                    'profesor': profesor,
                    'salon': form_salon or 'Aula 1',
                    'es_base': False,
                },
            )
            messages.success(request, 'Horario guardado correctamente.')
            return redirect(f"{request.path}?group={form_group_label}")
        else:
            messages.error(request, 'No se pudo procesar el horario. Verifique los datos enviados.')
            return redirect(f"{request.path}?group={selected_group_label}")

    schedule_map = {display: {slot['label']: None for slot in time_slots} for _, display in day_values}

    normal_slot_labels = [slot['label'] for slot in time_slots if slot['type'] != 'break']
    default_schedule_rows = BASE_SCHEDULES.get(selected_group_label)
    if default_schedule_rows:
        fixed_professors = get_fixed_professors(prefetch_materias=True)
        profesor_by_username = {prof.usuario.username: prof for prof in fixed_professors if prof.usuario}
        for row_index, default_row in enumerate(default_schedule_rows):
            if row_index >= len(normal_slot_labels):
                break
            slot_label = normal_slot_labels[row_index]
            for day_index, (_, day_label) in enumerate(day_values):
                raw_subject = str(default_row[day_index]).strip()
                if raw_subject and raw_subject not in ('—', '-', '---'):
                    subject_name, room_name, teacher_username = parse_schedule_entry(raw_subject, prof_lookup)
                    teacher_name = fixed_prof_map.get(teacher_username, teacher_username)
                    professor_obj = profesor_by_username.get(teacher_username)
                    materia_id = materia_lookup.get(normalize_name_key(subject_name))
                    schedule_map[day_label][slot_label] = {
                        'subject': subject_name,
                        'room': room_name,
                        'teacher': teacher_name,
                        'materia_id': materia_id,
                        'profesor_id': professor_obj.id if professor_obj else None,
                        'occupied': True,
                        'id': None,
                    }

    horarios = Horario.objects.filter(grupo=selected_group_raw).select_related('materia', 'profesor__usuario')

    fixed_prof_map = {username: display_name for display_name, username in FIXED_PROFESSORS}
    day_map = {raw: display for raw, display in day_values}
    for h in horarios:
        day_label = day_map.get(h.dia, h.dia.capitalize())
        slot_label = f"{h.hora_inicio.strftime('%H:%M')} - {h.hora_fin.strftime('%H:%M')}"
        if day_label in schedule_map and slot_label in schedule_map[day_label]:
            teacher_name = ''
            if h.profesor and h.profesor.usuario:
                teacher_name = fixed_prof_map.get(h.profesor.usuario.username, h.profesor.usuario.username)

            schedule_map[day_label][slot_label] = {
                'subject': h.materia.nombre if h.materia else '',
                'room': h.salon or '',
                'teacher': teacher_name,
                'materia_id': h.materia.id if h.materia else None,
                'profesor_id': h.profesor.id if h.profesor else None,
                'occupied': True,
                'id': h.id,
            }

    schedule_rows = []
    for slot in time_slots:
        if slot['type'] == 'break':
            schedule_rows.append({'slot': slot, 'break': True, 'cells': []})
            continue

        cells = []
        for day_key, day_label in day_values:
            cells.append({
                'day_key': day_key,
                'day_label': day_label,
                'slot_label': slot['label'],
                'cell': schedule_map[day_label][slot['label']],
            })

        schedule_rows.append({'slot': slot, 'break': False, 'cells': cells})

    teachers = sorted(
        get_fixed_professors(),
        key=lambda teacher: ('/' in str(teacher.display_name), str(teacher.display_name))
    )
    all_subjects = Materia.objects.order_by('nombre')
    subjects = []
    seen_subjects = set()
    for materia in all_subjects:
        normalized_name = normalize_materia_name(materia.nombre)
        if normalized_name and normalized_name not in seen_subjects:
            seen_subjects.add(normalized_name)
            materia.nombre = normalized_name
            subjects.append(materia)

    subjects = sorted(subjects, key=lambda materia: ('/' in str(materia.nombre), str(materia.nombre)))

    contexto = {
        'groups': groups,
        'selected_group': selected_group_label,
        'day_values': day_values,
        'time_slots': time_slots,
        'schedule_map': schedule_map,
        'schedule_rows': schedule_rows,
        'teachers': teachers,
        'subjects': subjects,
    }

    return render(request, 'usuarios/horarios.html', contexto)


@login_required
@user_passes_test(lambda u: u.is_staff)
def import_from_file(request):
    if request.method != 'POST':
        return redirect('panel_coordinador')

    data_file = Path(settings.BASE_DIR) / 'data' / 'profesores_materias.txt'
    if not data_file.exists():
        messages.error(request, 'Archivo de datos no encontrado')
        return redirect('panel_coordinador')

    out = io.StringIO()
    try:
        call_command('importar_profesores_materias', str(data_file), stdout=out)
        output_text = re.sub(r'\x1b\[[0-9;]*m', '', out.getvalue())
        messages.success(request, output_text)
    except Exception as e:
        messages.error(request, f'Error durante la importación: {e}')

    return redirect('panel_coordinador')


# =========================
# PANEL PROFESOR
# =========================
@login_required
def panel_profesor(request):
    return render(request, "usuarios/profesor.html")


# =========================
# PANEL ESTUDIANTE
# =========================
@login_required
def panel_estudiante(request):
    return render(request, "usuarios/estudiante.html")


# =========================
# PANEL DIRECTIVO
# =========================
@login_required
def panel_directivo(request):
    return render(request, "usuarios/directivo.html")


def import_preview(request):
    """Vista temporal: lee el archivo data/profesores_materias.txt y muestra
    un mapeo profesor -> lista de materias sin tocar la base de datos.
    """
    data_file = Path(settings.BASE_DIR) / 'data' / 'profesores_materias.txt'
    mapping = {}

    def normalize(s):
        value = re.sub(r"\s+", " ", s.strip())
        return re.sub(r"\.+$", "", value)

    if data_file.exists():
        raw_lines = data_file.read_text(encoding='utf-8').splitlines()
        for raw in raw_lines:
            if not raw or raw.strip().startswith('#'):
                continue
            materia_chunk, profesor_chunk = split_pair(raw)

            # split multiple materias and multiple profesores
            materias = [normalize(x) for x in re.split(r"\s*/\s*|,|\s{2,}", materia_chunk) if x.strip()]
            profes = [normalize(x) for x in re.split(r"\s*/\s*|,|\s{2,}", profesor_chunk) if x.strip()]

            for prof in profes:
                if prof not in mapping:
                    mapping[prof] = []
                for m in materias:
                    if m not in mapping[prof]:
                        mapping[prof].append(m)

    # sort mapping by professor name
    sorted_items = sorted(mapping.items(), key=lambda x: x[0])

    return render(request, 'usuarios/profesores_preview.html', {'items': sorted_items})

# =========================
# PERFIL COORDINADOR
# =========================
@login_required
def perfil_coordinador(request):

    perfil, created = PerfilCoordinador.objects.get_or_create(
        usuario=request.user
    )

    if request.method == 'POST':

        # =========================
        # DATOS USUARIO
        # =========================
        request.user.first_name = request.POST.get('first_name')
        request.user.email = request.POST.get('email')
        request.user.save()

        # =========================
        # DATOS PERFIL
        # =========================
        perfil.rol = request.POST.get('rol')
        perfil.telefono = request.POST.get('telefono')
        perfil.direccion = request.POST.get('direccion')
        perfil.biografia = request.POST.get('biografia')

        # =========================
        # FECHA
        # =========================
        fecha = request.POST.get('fecha')

        if fecha:
            perfil.fecha = fecha
        else:
            perfil.fecha = None

        # =========================
        # FOTO
        # =========================
        if 'foto' in request.FILES:
            perfil.foto = request.FILES['foto']

        perfil.save()

        messages.success(
            request,
            'Perfil actualizado correctamente.'
        )

        return redirect('perfil_coordinador')

    contexto = {
        'perfil': perfil
    }

    return render(
        request,
        'usuarios/perfil_coordinador.html',
        contexto
    )                                                                       