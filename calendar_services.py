# calendar_service.py
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

# ===== CONFIGURACIÓN =====
SERVICE_ACCOUNT_FILE = 'credentials.json'  # tu archivo de cuenta de servicio
SCOPES = ['https://www.googleapis.com/auth/calendar']

# ID del calendario donde se crearán las citas
# Puedes obtenerlo desde "Configuración y uso compartido" en Google Calendar
CALENDAR_ID = 'jwlioabel@gmail.com'

# Zona horaria local (ajústala si no estás en Lima)
TIMEZONE = 'America/Lima'


# ===== FUNCIÓN PRINCIPAL =====
def crear_cita(nombre_paciente, doctor, fecha, hora_inicio, duracion_min=30, correo_paciente=None, motivo=None):
    """
    Crea una cita médica en Google Calendar.

    Parámetros:
    - nombre_paciente: str
    - doctor: str
    - fecha: str en formato 'YYYY-MM-DD'
    - hora_inicio: str en formato 'HH:MM'
    - duracion_min: int (opcional, por defecto 30)
    - correo_paciente: str (opcional)
    - motivo: str (opcional)
    """

    # Autenticación
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )

    service = build('calendar', 'v3', credentials=creds)

    # Convertir fecha y hora al formato ISO con zona horaria
    tz = pytz.timezone(TIMEZONE)
    inicio = tz.localize(datetime.strptime(f"{fecha} {hora_inicio}", "%Y-%m-%d %H:%M"))
    fin = inicio + timedelta(minutes=duracion_min)

    # Crear cuerpo del evento
    event = {
        'summary': f'Cita médica - {doctor}',
        'description': f'Paciente: {nombre_paciente}\nMotivo: {motivo or "Consulta general"}',
        'start': {'dateTime': inicio.isoformat(), 'timeZone': TIMEZONE},
        'end': {'dateTime': fin.isoformat(), 'timeZone': TIMEZONE},
        'attendees': [{'email': correo_paciente}] if correo_paciente else [],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 60},    # recordatorio 1 hora antes
                {'method': 'popup', 'minutes': 10},    # recordatorio 10 min antes
            ],
        },
    }

    # Insertar evento en Google Calendar
    event_result = service.events().insert(
        calendarId=CALENDAR_ID, body=event
    ).execute()

    return {
        "status": "ok",
        "evento": event_result.get('htmlLink'),
        "inicio": inicio.strftime("%Y-%m-%d %H:%M"),
        "fin": fin.strftime("%Y-%m-%d %H:%M"),
        "paciente": nombre_paciente,
        "doctor": doctor
    }
