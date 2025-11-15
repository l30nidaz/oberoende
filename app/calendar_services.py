# calendar_services.py
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

CALENDLY_TOKEN = os.getenv('CALENDLY_TOKEN')
CALENDLY_EVENT_TYPE_URI = os.getenv('CALENDLY_EVENT_TYPE_URI')  # e.g., https://api.calendly.com/event_types/EVT_ID
CALENDLY_BASE_URL = 'https://api.calendly.com'
HEADERS = {
    'Authorization': f'Bearer {CALENDLY_TOKEN}',
    'Content-Type': 'application/json'
}

def generar_link_calendly(nombre_paciente, email_paciente=None, doctor=None, motivo=None):
    """
    Genera un link pre-filled para Calendly.
    Retorna: dict con link y detalles.
    """
    # Pre-fill params (Calendly soporta estos)
    params = {
        'invitee_name': nombre_paciente,
        'invitee_email': email_paciente or f"{nombre_paciente.lower().replace(' ', '.')}@ejemplo.com",  # Fallback si no hay email
        'custom_answers': [  # Custom fields si los tienes en event type
            {'question': 'Doctor preferido', 'answer': doctor or 'Cualquiera'},
            {'question': 'Motivo de consulta', 'answer': motivo or 'Consulta general'}
        ]
    }
    
    # Construye el scheduling link (usa el event type URI para base)
    event_type_id = CALENDLY_EVENT_TYPE_URI.split('/')[-1]
    base_link = f"https://calendly.com/{event_type_id.replace('event_types/', '')}/schedule"
    
    # Append params (Calendly parsea query strings)
    import urllib.parse
    query_string = urllib.parse.urlencode({k: v for k, v in params.items() if isinstance(v, str)}, doseq=True)
    full_link = f"{base_link}?{query_string}"
    
    return {
        "status": "ok",
        "link": full_link,
        "mensaje_whatsapp": f"¡Hola {nombre_paciente}! Agenda tu cita aquí: {full_link}\n\nElige doctor: {doctor or 'Disponible'}\nMotivo: {motivo or 'Consulta general'}",
        "paciente": nombre_paciente,
        "doctor": doctor
    }

def chequear_disponibilidad(doctor_uri=None, fecha_inicio=None, fecha_fin=None):
    """
    Chequea slots disponibles en event type (opcional, para pre-filtrar).
    """
    params = {}
    if fecha_inicio:
        params['start_time'] = fecha_inicio  # ISO format
    if fecha_fin:
        params['end_time'] = fecha_fin
    if doctor_uri:  # Si es team event
        params['preferred_organization_user'] = doctor_uri  # URI del doctor
    
    response = requests.get(
        f"{CALENDLY_BASE_URL}/event_types/{CALENDLY_EVENT_TYPE_URI.split('/')[-1]}/availability",
        headers=HEADERS,
        params=params
    )
    
    if response.status_code == 200:
        data = response.json()
        slots = data.get('resource', {}).get('slots', [])  # Lista de slots disponibles
        return {"disponibles": slots[:5]}  # Top 5 slots
    else:
        return {"error": response.text}

def manejar_webhook_calendly(data):
    """
    Procesa webhook cuando se crea invitado (cita agendada).
    Llama esto desde tu endpoint Flask.
    Retorna: dict con detalles para DB o WhatsApp confirm.
    """
    if data.get('event') == 'invitee.created':
        invitee = data['payload']['invitee']
        event = data['payload']['event']  # Detalles del evento
        
        # Actualiza tu DB (usa tu modelo Appointment)
        # Ejemplo: from app.appointments import Appointment; Appointment.create_from_calendly(invitee)
        
        # Envía confirmación por WhatsApp (integra con tu send_whatsapp_message)
        confirm_msg = f"✅ Cita confirmada para {invitee['name']} el {event['start_time']} con {event.get('organization_user', {}).get('name', 'Doctor asignado')}."
        
        return {
            "status": "ok",
            "confirmacion": confirm_msg,
            "detalles": {
                "paciente": invitee['name'],
                "fecha": event['start_time'],
                "doctor": event.get('organization_user', {}).get('name')
            }
        }
    return {"status": "ignored"}

# Mantén tu función vieja como fallback si quieres
# def crear_cita_google(...): ...  # Tu código original