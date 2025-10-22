from app import db

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    patient_phone = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, confirmed, canceled, no_show

    def to_dict(self):
        return f"<Appointment {self.id} - {self.patient_name} on {self.date} at {self.time}>"