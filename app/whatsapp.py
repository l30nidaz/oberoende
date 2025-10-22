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


load_dotenv()
MODEL = os.getenv("MODEL_NAME", "gpt-5-nano")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
account_sid = os.getenv('TWILIO_ACCOUNT_SID') 
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_client = Client(account_sid, auth_token)
client_openai = OpenAI()
#openai.api_key = OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
bp = Blueprint('whatsapp', __name__)


# Función para recuperar contexto con Chroma
def recuperar_contexto(pregunta, top_k=3):
    results = mi_coleccion.query(
        query_texts=[pregunta],
        n_results=top_k
    )
    docs = results["documents"][0]
    print(f"[Debug] Docs para pregunta «{pregunta}»: {docs}")
    return docs



# Función para generar la respuesta vía OpenAI
def generar_respuesta(pregunta, contexto_docs, saludo: str = ""):
    # Construir prompt
    contexto_list = contexto_docs if isinstance(contexto_docs, list) else [contexto_docs]
    contexto_text = "\n---\n".join(contexto_list)
    prompt = f"""

                Instrucción al asistente:  
                    si crees que debes hacerlo saluda al usuario con esta expresión {saludo}, si no, no
                    Actúa como Oberoende, un asesor empresarial experto en chatbots, integraciones y automatización. Responde de forma profesional, en un solo párrafo claro, evitando jerga técnica innecesaria.
                    .
                Información de referencia:  
                {contexto_text}

                Consulta del usuario: {pregunta}

                    Tu respuesta:"""
    
    print("[DEBUG] Prompt enviado al modelo:", prompt)

    response = client_openai.chat.completions.create(
        model=os.getenv('MODEL_NAME'),  
        messages=[
            {"role": "system",  "content": "Eres Oberoende, el asistente de la empresa."},
            {"role": "user",    "content": prompt}
        ],
        max_completion_tokens=300
        #,temperature=0.2 Unsoported to model gpt-5-nano
    )
    respuesta_texto = response.choices[0].message.content.strip()
    print("[DEBUG] Respuesta generada:", respuesta_texto)
    return respuesta_texto


# Función para enviar un mensaje de WhatsApp usando Twilio
def enviar_whatsapp(to_number, body_text):
    message = twilio_client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        to=to_number,
        body=body_text
    )
    return message.sid


@bp.route("/whatsapp_webhook", methods=["POST"])
@csrf.exempt  # esto desactiva CSRF solo para esta ruta
def whatsapp_webhook():
    from_number = request.form.get("From")
    body       = request.form.get("Body")
    if not from_number or not body:
        # Bad request
        return ("mensaje que indica bad request en la función whatsapp_webhook", 400)
    
    usuario = get_or_create_usuario(from_number)


    # Saludo condicionado
    if usuario.primer_contacto:
        saludo = f"Hola {usuario.nombre}," if usuario.nombre else "Hola,"
        usuario.primer_contacto = False
        db.session.commit()
    else:
        saludo = "Hola de nuevo,"
    
    # Recuperar contexto
    contexto = recuperar_contexto(body, top_k=3)

    # Generar respuesta
    respuesta = generar_respuesta(body, contexto, saludo=saludo)
    
    try:
        if not respuesta or respuesta.strip() == "":
            respuesta = "No tengo información suficiente para responder en este momento."
        enviar_whatsapp(to_number=from_number, body_text=respuesta)
    except Exception as e:
        # Opcional: loguear el error
        print("Error enviando WhatsApp:", e)
    return jsonify({"status": "ok", "mensaje_enviado": respuesta})
 

def send_whatsapp_message(to_whatsapp_number, message_text):
    account_sid = os.getenv('TWILIO_ACCOUNT_SID') 
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_client = Client(account_sid, auth_token)
    message = twilio_client.messages.create(
        from_ = os.getenv('TWILIO_WHATSAPP_NUMBER'),  # número de Twilio para WhatsApp
        to = to_whatsapp_number,
        body = message_text
    )
    return message.sid
