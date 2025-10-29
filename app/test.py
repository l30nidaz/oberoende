from calendar_services import crear_cita
from app.whatsapp import enviar_whatsapp
nombre_paciente = "Juan Pérez"
doctor = "Dr. García"
fecha = "2025-10-23"
hora = "09:00"
correo_paciente = "juanperez@gmail.com"

resultado = crear_cita(nombre_paciente, doctor, fecha, hora, correo_paciente=correo_paciente)

print("Cita creada correctamente:")
enviar_whatsapp("952834431","Cita creada correctamente")
print(resultado)

