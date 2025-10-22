from flask import Blueprint, jsonify
import tiktoken
from dotenv import load_dotenv
import os

load_dotenv()
MODEL=os.getenv("MODEL_NAME", "gpt-5-nano")  # Modelo por defecto si no está en .env

bp = Blueprint('functions', __name__)


def count_tokens_model(text: str, model_name: str = MODEL) -> int:
    encoding = tiktoken.encoding_for_model(model_name)
    return len(encoding.encode(text))

# Manejo global de errores (opcional pero recomendable)
@bp.errorhandler(500)
def handle_internal_error(e):
    # Aquí puedes registrar e internamente el error, por ejemplo con logging
    return jsonify({"error": "Ha ocurrido un error interno"}), 500

@bp.errorhandler(404)
def handle_not_found(e):
    return jsonify({"error": "Recurso no encontrado"}), 404

@bp.errorhandler(400)
def handle_not_found(e):
    return jsonify({"error": "BAD Requeste"}), 400