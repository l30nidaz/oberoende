from app.whatsapp import enviar_whatsapp
from flask import jsonify, Blueprint
import os
from openai import OpenAI
import json
client_openai = OpenAI()

bp = Blueprint('citas', __name__)

def detectar_intencion_cita(mensaje: str) -> bool:
    palabras_clave = [
        "cita", "agendar", "reservar", "consultar", "horario", 
        "disponibilidad", "odontólogo", "dentista", "limpieza",
        "extracción", "blanqueamiento", "ortodoncia", "consulta"
    ]
    mensaje_lower = mensaje.lower()
    return any(palabra in mensaje_lower for palabra in palabras_clave)


def manejar_solicitud_cita(from_number: str, mensaje: str, usuario):
    """Maneja el flujo completo de agendamiento de citas"""
    
    # Extraer información del mensaje usando OpenAI
    info_cita = extraer_info_cita(mensaje, usuario)
    
    if not info_cita.get("servicio"):
        # Preguntar por el servicio
        enviar_whatsapp(from_number, "¿Para qué servicio dental te gustaría agendar cita? (limpieza, extracción, blanqueamiento, etc.)")
        return jsonify({"status": "pending_service"})
    
    if not info_cita.get("fecha"):
        # Mostrar disponibilidad
        disponibilidad = obtener_disponibilidad()
        mensaje_disponibilidad = format_disponibilidad(disponibilidad)
        enviar_whatsapp(from_number, f"Tenemos estos horarios disponibles:\n{mensaje_disponibilidad}\n¿Qué día y hora prefieres?")
        return jsonify({"status": "pending_datetime"})
    
    # Intentar crear la cita
    try:
        response = crear_cita_via_api(info_cita)
        if response.status_code == 201:
            enviar_whatsapp(from_number, f"✅ Cita confirmada!\n📅 {info_cita['fecha']} a las {info_cita['hora']}\n🦷 {info_cita['servicio']}\n📍 Clínica Dental Sonrisa Saludable")
        else:
            enviar_whatsapp(from_number, "❌ Lo siento, ese horario ya no está disponible. ¿Podrías elegir otro?")
    except Exception as e:
        enviar_whatsapp(from_number, "❌ Error al agendar la cita. Por favor, intenta de nuevo.")
    
    return jsonify({"status": "completed"})

def extraer_info_cita(mensaje: str, usuario):
    """Usa OpenAI para extraer información estructurada de la solicitud de cita"""
    
    prompt = f"""
    Extrae información sobre una cita dental del siguiente mensaje:
    Mensaje: "{mensaje}"
    
    Información del usuario:
    - Nombre: {usuario.nombre or 'No proporcionado'}
    - Teléfono: {usuario.numero_whatsapp}
    
    Devuelve JSON con:
    - servicio: tipo de servicio dental (limpieza, extracción, etc.)
    - fecha: fecha en formato YYYY-MM-DD (si se menciona)
    - hora: hora en formato HH:MM:SS (si se menciona)
    - urgencia: true/false si es emergencia
    
    Si falta información, deja el campo vacío.
    """
    
    try:
        response = client_openai.chat.completions.create(
            model=os.getenv('MODEL_NAME'),
            messages=[
                {"role": "system", "content": "Eres un asistente que extrae información estructurada de solicitudes de citas dentales."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"servicio": "", "fecha": "", "hora": "", "urgencia": False}
    

def obtener_disponibilidad(dias=7):
    """Obtiene horarios disponibles para los próximos días"""
    from datetime import datetime, timedelta
    
    disponibilidad = []
    hoy = datetime.now().date()
    
    for i in range(dias):
        fecha = hoy + timedelta(days=i)
        # Aquí integrarías con Calendly o generarías horarios estándar
        if fecha.weekday() < 5:  # Lunes a Viernes
            horarios = ["09:00:00", "10:00:00", "11:00:00", "15:00:00", "16:00:00", "17:00:00"]
        else:  # Sábado
            horarios = ["09:00:00", "10:00:00", "11:00:00"]
        
        # Filtrar horarios ya ocupados
        horarios_disponibles = filtrar_horarios_ocupados(fecha, horarios)
        
        if horarios_disponibles:
            disponibilidad.append({
                "fecha": fecha.strftime("%Y-%m-%d"),
                "dia_semana": fecha.strftime("%A"),
                "horarios": horarios_disponibles
            })
    
    return disponibilidad

def filtrar_horarios_ocupados(fecha, horarios):
    """Filtra horarios ya ocupados en la base de datos"""
    from app.models import Appointment
    from datetime import time
    
    citas_ocupadas = Appointment.query.filter_by(
        date=fecha
    ).filter(
        Appointment.status.in_(['pending', 'confirmed'])
    ).all()
    
    horarios_ocupados = [cita.time.strftime("%H:%M:%S") for cita in citas_ocupadas]
    return [h for h in horarios if h not in horarios_ocupados]

def format_disponibilidad(disponibilidad):
    """Formatea la disponibilidad para enviar por WhatsApp"""
    mensaje = ""
    for dia in disponibilidad[:3]:  # Mostrar solo próximos 3 días
        mensaje += f"\n📅 {dia['dia_semana']} ({dia['fecha']}):\n"
        mensaje += " • " + " • ".join([h[:5] for h in dia['horarios']]) + "\n"
    return mensaje

def crear_cita_via_api(info_cita):
    """Usa tu endpoint existente de appointments para crear la cita"""
    import requests
    
    data = {
        "name": info_cita.get("nombre", "Cliente WhatsApp"),
        "phone": info_cita.get("telefono"),
        "service": info_cita["servicio"],
        "date": info_cita["fecha"],
        "time": info_cita["hora"]
    }
    
    # Llama a tu propio endpoint
    response = requests.post(
        "http://localhost:5000/appointments/appointments",  # Ajusta la URL
        json=data
    )
    return response