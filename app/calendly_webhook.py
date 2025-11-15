import os
from flask import Blueprint, request, jsonify
from app.calendar_services import manejar_webhook_calendly
from twilio.rest import Client  # Para enviar confirm por WhatsApp

bp = Blueprint('calendly', __name__)

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_client = Client(account_sid, auth_token)

@bp.route("/calendly_webhook", methods=["POST"])
def calendly_webhook():
    data = request.json  # Calendly envía JSON
    print(f"[WEBHOOK] Datos de Calendly: {data}")
    
    resultado = manejar_webhook_calendly(data)
    
    if resultado['status'] == 'ok':
        # Envía confirm por WhatsApp (usa el número del invitee)
        invitee_phone = data['payload']['invitee'].get('phone_number')  # Si lo capturas en Calendly
        if invitee_phone:
            twilio_client.messages.create(
                from_=os.getenv('TWILIO_WHATSAPP_NUMBER'),
                to=invitee_phone,
                body=resultado['confirmacion']
            )
        # Actualiza DB aquí si quieres (e.g., Appointment.from_calendly(resultado['detalles']))
    
    return jsonify({"status": "ok"}), 200  # Calendly espera 200