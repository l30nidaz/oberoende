# app/users.py
from flask import Blueprint, request, jsonify
from app import db  # tu instancia de SQLAlchemy
from datetime import datetime, timezone

bp = Blueprint('users', __name__, url_prefix='/users')

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    numero_whatsapp = db.Column(db.String(32), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=True)
    fecha_creacion = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    primer_contacto = db.Column(db.Boolean, default=True)  # nuevo campo

    def __repr__(self):
        return f"<Usuario {self.numero_whatsapp} nombre={self.nombre} primer_contacto={self.primer_contacto}>"

def get_or_create_usuario(numero_whatsapp: str) -> Usuario:
    usuario = Usuario.query.filter_by(numero_whatsapp=numero_whatsapp).first()
    if not usuario:
        usuario = Usuario(numero_whatsapp=numero_whatsapp)
        db.session.add(usuario)
        db.session.commit()
    return usuario

@bp.route('/profile', methods=['GET'])
def obtener_perfil():
    numero = request.args.get('numero')
    if not numero:
        return jsonify({"error": "Se requiere parámetro 'numero'"}), 400
    usuario = Usuario.query.filter_by(numero_whatsapp=numero).first()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify({
        "id": usuario.id,
        "numero_whatsapp": usuario.numero_whatsapp,
        "nombre": usuario.nombre,
        "fecha_creacion": usuario.fecha_creacion.isoformat(),
        "primer_contacto": usuario.primer_contacto
    }), 200
