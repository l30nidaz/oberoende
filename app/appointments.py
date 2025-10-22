from datetime import date, datetime, time
from flask import jsonify, request, Blueprint
from app.models import Appointment, db


bp  = Blueprint('appointments', __name__, url_prefix='/appointments')

@bp.route("/appointments", methods=["POST"])
def create_appointment():
    data = request.get_json()
    name = data.get("name")
    phone = data.get("phone")
    service = data.get("service")
    date_str = data.get("date")   # espera "YYYY-MM-DD"
    time_str = data.get("time")   # espera "HH:MM:SS"

    # Validación de campos obligatorios
    if not all([name, phone, service, date_str, time_str]):
        return jsonify({"error": "Faltan datos requeridos"}), 400

    # Validar formato de fecha y hora
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Formato de fecha inválido, use YYYY-MM-DD"}), 400

    try:
        time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
    except ValueError:
        return jsonify({"error": "Formato de hora inválido, use HH:MM:SS"}), 400

    # Validar que la fecha no esté en el pasado
    today = date.today()
    if date_obj < today:
        return jsonify({"error": "No se puede reservar para fechas pasadas"}), 400

    # Validar horario de atención permitido (ejemplo: 9:00 a 19:00)
    hora_inicio = time(hour=9, minute=0, second=0)
    hora_fin = time(hour=19, minute=0, second=0)
    if not (hora_inicio <= time_obj <= hora_fin):
        return jsonify({"error": "Hora fuera del horario de atención"}), 400

    # Validar que la cita sea múltiplo de 30 minutos (ejemplos: :00 o :30)
    if time_obj.minute % 30 != 0 or time_obj.second != 0:
        return jsonify({"error": "La cita debe ser en intervalos de 30 minutos"}), 400

    # Verificar solapamientos (otra cita en misma fecha y hora y estado que no sea cancelado)
    existing = Appointment.query.filter_by(date=date_obj, time=time_obj)\
        .filter(Appointment.status != 'canceled')\
        .first()
    if existing:
        return jsonify({"error": "Ya hay una cita en ese horario"}), 409

    # Si todo pasa, crear la cita
    new_app = Appointment(
        patient_name=name,
        patient_phone=phone,
        service_type=service,
        date=date_obj,
        time=time_obj,
        status='pending'
    )
    db.session.add(new_app)
    db.session.commit()

    return jsonify({"message": "Cita creada", "appointment_id": new_app.id}), 201

VALID_STATUSES = {"pending", "confirmed", "canceled", "no_show"}

@bp.route("/appointments/<int:app_id>", methods=["PUT"])
def update_appointment(app_id):
    data = request.get_json()
    # Puedes permitir cambiar estado, reprogramar fecha/hora, motivo servicio, etc.
    status = data.get("status")
    new_date_str = data.get("date")
    new_time_str = data.get("time")

    appdb = Appointment.query.get(app_id)
    if not appdb:
        return jsonify({"error": "Cita no encontrada"}), 404

    # Si se pide cambiar estado:
    if status is not None:
        if status not in VALID_STATUSES:
            return jsonify({"error": f"Estado inválido. Debe ser uno de {list(VALID_STATUSES)}"}), 400
        appdb.status = status

    # Si se pide reprogramar fecha/hora juntos:
    if new_date_str is not None and new_time_str is not None:
        # Validar formato
        try:
            new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido, use YYYY-MM-DD"}), 400

        try:
            new_time = datetime.strptime(new_time_str, "%H:%M:%S").time()
        except ValueError:
            return jsonify({"error": "Formato de hora inválido, use HH:MM:SS"}), 400

        # Validar fecha no pasada
        if new_date < date.today():
            return jsonify({"error": "No se puede reprogramar a una fecha pasada"}), 400

        # Validar horario permitido (ej: 9:00 a 19:00)
        hora_inicio = time(9, 0, 0)
        hora_fin = time(19, 0, 0)
        if not (hora_inicio <= new_time <= hora_fin):
            return jsonify({"error": "Hora fuera del horario de atención"}), 400

        # Validar múltiplo de 30 minutos
        if new_time.minute % 30 != 0 or new_time.second != 0:
            return jsonify({"error": "La reprogramación debe ser en intervalos de 30 minutos"}), 400

        # Verificar que no hay otra cita en ese horario
        conflict = Appointment.query.filter_by(date=new_date, time=new_time)\
            .filter(Appointment.status != 'canceled')\
            .first()
        # Si la cita conflictiva no es la misma que estamos actualizando
        if conflict and conflict.id != appdb.id:
            return jsonify({"error": "Ya existe otra cita en ese horario"}), 409

        # Si todo bien, asignar
        appdb.date = new_date
        appdb.time = new_time

    # Guardar cambios
    db.session.commit()

    return jsonify({
        "message": "Cita actualizada",
        "appointment_id": appdb.id,
        "new_date": str(appdb.date),
        "new_time": str(appdb.time),
        "status": appdb.status
    }), 200
