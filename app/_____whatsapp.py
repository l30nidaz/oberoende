from flask import Blueprint, jsonify, request, Response
import chromadb
from openai import OpenAI
from chromadb.utils import embedding_functions
from twilio.twiml.messaging_response import MessagingResponse
from app.users import get_or_create_usuario
from twilio.rest import Client
from app.functions import count_tokens_model
from app import db
from dotenv import load_dotenv
import os
from app.my_collections import mi_coleccion 
from app import csrf
from app.___calendar_services import crear_cita
import json
import re
from datetime import datetime, timedelta


load_dotenv()
MODEL = os.getenv("MODEL_NAME", "grok-3")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
account_sid = os.getenv('TWILIO_ACCOUNT_SID') 
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_client = Client(account_sid, auth_token)
#client_openai = OpenAI()
client_openai = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)
bp = Blueprint('whatsapp', __name__)


# Estructura para mantener el estado de la conversación
# En producción, esto debería estar en Redis o en la base de datos
conversation_states = {}


def detectar_intencion(mensaje):
    """
    Detecta la intención del usuario usando GPT.
    Retorna: dict con 'intencion' y 'entidades' extraídas
    """
    prompt = f"""
Analiza el siguiente mensaje del usuario y determina su intención principal.

Mensaje: "{mensaje}"

Responde SOLO con un JSON válido en este formato:
{{
    "intencion": "agendar_cita" | "cancelar_cita" | "reprogramar_cita" | "consulta_general",
    "entidades": {{
        "nombre_paciente": "nombre si lo menciona o null",
        "doctor": "nombre del doctor si lo menciona o null",
        "fecha": "fecha en formato YYYY-MM-DD si la menciona o null",
        "hora": "hora en formato HH:MM si la menciona o null",
        "motivo": "motivo de la cita si lo menciona o null"
    }}
}}

Ejemplos:
- "Quiero agendar una cita" -> {{"intencion": "agendar_cita", "entidades": {{}}}}
- "Necesito cancelar mi cita del martes" -> {{"intencion": "cancelar_cita", "entidades": {{}}}}
- "Hola, soy Juan y quiero una cita con el Dr. Pérez para el 15 de diciembre a las 3pm" -> {{"intencion": "agendar_cita", "entidades": {{"nombre_paciente": "Juan", "doctor": "Dr. Pérez", "fecha": "2024-12-15", "hora": "15:00"}}}}
"""
    
    try:
        response = client_openai.chat.completions.create(
            model=os.getenv('MODEL_NAME'),
            messages=[
                {"role": "system", "content": "Eres un asistente que extrae intenciones y entidades de mensajes. Responde SOLO con JSON válido."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=300
        )
        
        resultado = response.choices[0].message.content.strip()
        # Limpiar posibles markdown
        resultado = resultado.replace("```json", "").replace("```", "").strip()
        return json.loads(resultado)
    except Exception as e:
        print(f"[ERROR] detectar_intencion: {e}")
        return {"intencion": "consulta_general", "entidades": {}}


def validar_y_normalizar_fecha(fecha_texto, mensaje_original):
    """
    Valida y convierte fechas relativas (hoy, mañana, lunes) a formato YYYY-MM-DD
    """
    prompt = f"""
Convierte la siguiente referencia de fecha al formato YYYY-MM-DD.
Hoy es {datetime.now().strftime('%Y-%m-%d')} ({datetime.now().strftime('%A')}).

Fecha mencionada: "{fecha_texto}"
Contexto: "{mensaje_original}"

Responde SOLO con la fecha en formato YYYY-MM-DD o "invalido" si no se puede determinar.
Ejemplos:
- "hoy" -> {datetime.now().strftime('%Y-%m-%d')}
- "mañana" -> {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}
- "lunes" -> (el próximo lunes)
- "15 de diciembre" -> 2024-12-15
"""
    
    try:
        response = client_openai.chat.completions.create(
            model=os.getenv('MODEL_NAME'),
            messages=[
                {"role": "system", "content": "Convierte fechas a formato YYYY-MM-DD."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=50
        )
        fecha_normalizada = response.choices[0].message.content.strip()
        
        # Validar formato
        datetime.strptime(fecha_normalizada, '%Y-%m-%d')
        return fecha_normalizada
    except:
        return None


def validar_y_normalizar_hora(hora_texto):
    """
    Convierte formatos de hora variados a HH:MM formato 24h
    """
    # Patrones comunes
    patrones = [
        (r'(\d{1,2})\s*(?:de la\s*)?(?:pm|p\.m\.|tarde)', lambda m: f"{int(m.group(1)) + 12 if int(m.group(1)) < 12 else int(m.group(1))}:00"),
        (r'(\d{1,2})\s*(?:am|a\.m\.|mañana)', lambda m: f"{int(m.group(1)):02d}:00"),
        (r'(\d{1,2}):(\d{2})', lambda m: f"{int(m.group(1)):02d}:{m.group(2)}"),
        (r'(\d{1,2})\s*h', lambda m: f"{int(m.group(1)):02d}:00"),
    ]
    
    hora_lower = hora_texto.lower()
    for patron, convertir in patrones:
        match = re.search(patron, hora_lower)
        if match:
            try:
                hora = convertir(match)
                # Validar formato HH:MM
                datetime.strptime(hora, '%H:%M')
                return hora
            except:
                continue
    
    return None


def gestionar_flujo_cita(usuario, mensaje, state):
    """
    Gestiona el flujo conversacional para agendar una cita
    """
    # Extraer información del mensaje actual
    intencion_data = detectar_intencion(mensaje)
    entidades = intencion_data.get('entidades', {})
    
    # Actualizar state con nuevas entidades
    for key, value in entidades.items():
        if value and value != "null":
            state[key] = value
    
    # Campos requeridos
    campos_requeridos = {
        'nombre_paciente': '¿Cuál es tu nombre completo?',
        'doctor': '¿Con qué doctor deseas la cita?',
        'fecha': '¿Para qué fecha? (puedes decir: hoy, mañana, lunes, o una fecha específica)',
        'hora': '¿A qué hora prefieres? (ejemplo: 3pm, 15:00, 10 de la mañana)',
        'motivo': '¿Cuál es el motivo de tu consulta? (opcional, escribe "ninguno" para omitir)'
    }
    
    # Verificar qué falta
    for campo, pregunta in campos_requeridos.items():
        if campo not in state or not state[campo]:
            return {
                'completado': False,
                'respuesta': pregunta,
                'state': state
            }
    
    # Validar y normalizar fecha
    if state['fecha'] and not re.match(r'\d{4}-\d{2}-\d{2}', state['fecha']):
        fecha_normalizada = validar_y_normalizar_fecha(state['fecha'], mensaje)
        if not fecha_normalizada:
            state.pop('fecha', None)
            return {
                'completado': False,
                'respuesta': 'No pude entender la fecha. ¿Puedes especificarla de nuevo? (ejemplo: 15 de diciembre, mañana, lunes)',
                'state': state
            }
        state['fecha'] = fecha_normalizada
    
    # Validar y normalizar hora
    if state['hora'] and not re.match(r'\d{2}:\d{2}', state['hora']):
        hora_normalizada = validar_y_normalizar_hora(state['hora'])
        if not hora_normalizada:
            state.pop('hora', None)
            return {
                'completado': False,
                'respuesta': 'No pude entender la hora. ¿Puedes especificarla de nuevo? (ejemplo: 3pm, 15:00)',
                'state': state
            }
        state['hora'] = hora_normalizada
    
    # Todos los campos completos - crear cita
    try:
        resultado = crear_cita(
            nombre_paciente=state['nombre_paciente'],
            doctor=state['doctor'],
            fecha=state['fecha'],
            hora_inicio=state['hora'],
            duracion_min=30,
            correo_paciente=usuario.email if hasattr(usuario, 'email') else None,
            motivo=state.get('motivo', 'Consulta general')
        )
        
        respuesta = f"""
✅ ¡Cita agendada exitosamente!

📋 Detalles:
• Paciente: {resultado['paciente']}
• Doctor: {resultado['doctor']}
• Fecha: {resultado['inicio']}
• Duración: 30 minutos

Te enviaremos recordatorios antes de tu cita. ¿Hay algo más en lo que pueda ayudarte?
"""
        
        return {
            'completado': True,
            'respuesta': respuesta.strip(),
            'state': {}  # Limpiar state
        }
    except Exception as e:
        print(f"[ERROR] crear_cita: {e}")
        return {
            'completado': False,
            'respuesta': f'Hubo un error al crear la cita: {str(e)}. ¿Quieres intentarlo de nuevo?',
            'state': {}
        }


def recuperar_contexto(pregunta, top_k=3):
    results = mi_coleccion.query(
        query_texts=[pregunta],
        n_results=top_k
    )
    docs = results["documents"][0]
    print(f"[Debug] Docs para pregunta «{pregunta}»: {docs}")
    return docs


def generar_respuesta(pregunta, contexto_docs, saludo: str = ""):
    contexto_list = contexto_docs if isinstance(contexto_docs, list) else [contexto_docs]
    contexto_text = "\n---\n".join(contexto_list)
    prompt = f"""
Instrucción al asistente:  
    {saludo if saludo else ""}
    Actúa como Oberoende, un asesor empresarial experto en chatbots, integraciones y automatización. Responde de forma profesional, en un solo párrafo claro, evitando jerga técnica innecesaria.

Información de referencia:  
{contexto_text}

Consulta del usuario: {pregunta}

Tu respuesta:"""
    
    response = client_openai.chat.completions.create(
        model=os.getenv('MODEL_NAME'),  
        messages=[
            {"role": "system", "content": "Eres Oberoende, el asistente de la empresa."},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=300
    )
    respuesta_texto = response.choices[0].message.content.strip()
    return respuesta_texto


def enviar_whatsapp(to_number, body_text):
    message = twilio_client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        to=to_number,
        body=body_text
    )
    return message.sid


@bp.route("/whatsapp_webhook", methods=["POST"])
@csrf.exempt
def whatsapp_webhook():
    from_number = request.form.get("From")
    body = request.form.get("Body")
    
    if not from_number or not body:
        return ("Bad request - Faltan parámetros", 400)
    
    usuario = get_or_create_usuario(from_number)
    
    # Saludo condicionado
    if usuario.primer_contacto:
        saludo = f"Hola {usuario.nombre}," if usuario.nombre else "Hola,"
        usuario.primer_contacto = False
        db.session.commit()
    else:
        saludo = ""
    
    # Obtener o inicializar estado de conversación
    user_state = conversation_states.get(from_number, {
        'intencion': None,
        'data': {}
    })
    
    # Detectar intención si no hay una activa
    if not user_state['intencion']:
        intencion_data = detectar_intencion(body)
        intencion = intencion_data['intencion']
        
        if intencion == 'agendar_cita':
            user_state['intencion'] = 'agendar_cita'
            user_state['data'] = intencion_data.get('entidades', {})
            conversation_states[from_number] = user_state
            
            resultado = gestionar_flujo_cita(usuario, body, user_state['data'])
            respuesta = resultado['respuesta']
            
            if resultado['completado']:
                # Limpiar estado
                conversation_states.pop(from_number, None)
            else:
                # Actualizar estado
                user_state['data'] = resultado['state']
                conversation_states[from_number] = user_state
        
        elif intencion == 'cancelar_cita':
            # TODO: Implementar flujo de cancelación
            respuesta = "Para cancelar tu cita, por favor contáctanos al teléfono de la clínica. Estamos trabajando en habilitar esta función pronto."
            conversation_states.pop(from_number, None)
        
        elif intencion == 'reprogramar_cita':
            # TODO: Implementar flujo de reprogramación
            respuesta = "Para reprogramar tu cita, por favor contáctanos al teléfono de la clínica. Estamos trabajando en habilitar esta función pronto."
            conversation_states.pop(from_number, None)
        
        else:
            # Consulta general - usar RAG normal
            contexto = recuperar_contexto(body, top_k=3)
            respuesta = generar_respuesta(body, contexto, saludo=saludo)
    
    else:
        # Continuar con flujo activo
        if user_state['intencion'] == 'agendar_cita':
            resultado = gestionar_flujo_cita(usuario, body, user_state['data'])
            respuesta = resultado['respuesta']
            
            if resultado['completado']:
                conversation_states.pop(from_number, None)
            else:
                user_state['data'] = resultado['state']
                conversation_states[from_number] = user_state
    
    # Enviar respuesta
    try:
        if not respuesta or respuesta.strip() == "":
            respuesta = "No tengo información suficiente para responder en este momento."
        
        codigo_de_envio = enviar_whatsapp(to_number=from_number, body_text=respuesta)
        print(f"[INFO] Mensaje enviado. SID: {codigo_de_envio}")
    except Exception as e:
        print(f"[ERROR] Error enviando WhatsApp: {e}")
        return jsonify({"status": "error", "mensaje": str(e)}), 500
    
    return jsonify({"status": "ok", "mensaje_enviado": respuesta})


def send_whatsapp_message(to_whatsapp_number, message_text):
    message = twilio_client.messages.create(
        from_=os.getenv('TWILIO_WHATSAPP_NUMBER'),
        to=to_whatsapp_number,
        body=message_text
    )
    return message.sid