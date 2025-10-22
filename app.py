from flask import Flask, request, jsonify, Response, render_template
from flask_sqlalchemy import SQLAlchemy
from app.functions import count_tokens_model
from openai import OpenAI
import os
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
import tiktoken
from datetime import datetime
from flask_wtf.csrf import CSRFProtect
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

load_dotenv()
db = SQLAlchemy()
app = Flask(__name__)
# El secret_key firma las cookies de sesión y otros datos sensibles
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY") or os.urandom(32)

# Asegura que las cookies de sesión no sean accesibles vía JavaScript
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Mitiga ataques de CSRF al restringir el envío de cookies en solicitudes cross-site
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # evita CSRF en muchos casos

# --- CSRF Protection para rutas que usan formularios / POST --- #
csrf = CSRFProtect(app)
# Puedes eximir rutas que no necesites, por ejemplo las rutas de webhooks
# con @csrf.exempt
# Configurar DB MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("MYSQL_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

