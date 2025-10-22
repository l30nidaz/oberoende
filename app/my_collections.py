import chromadb
from flask import Blueprint

bp = Blueprint('my_collections', __name__)


chroma_client = chromadb.Client()
mi_coleccion = chroma_client.create_collection(name="mi_coleccion")


# Textos de ejemplo (pueden ser respuestas, información de empresa, etc.)
documentos = [
    "Oberoende ofrece soluciones de chatbots conectados con WhatsApp y otras plataformas.",
    "Nuestros chatbots pueden responder preguntas frecuentes y automatizar tareas repetitivas.",
    "Implementamos integraciones personalizadas usando Twilio, Flask y APIs REST.",
    "Los modelos de lenguaje permiten mejorar la comprensión del contexto y dar respuestas más naturales."
    "Oberoende es la empresa que… ofrece soluciones de chatbots conectados con WhatsApp… y otras plataformas.",
]

# Agregamos los documentos a la colección con sus embeddings
mi_coleccion.add(
    documents=documentos,
    ids=[f"doc_{i}" for i in range(len(documentos))]
)

# En my_collections.py - Agregar documentos dentales
documentos_odontologia = [
    "Limpieza dental: procedimiento de 45 minutos, requiere ayuno de 2 horas antes",
    "Extracción dental: procedimiento de 60 minutos, necesita radiografía previa",
    "Blanqueamiento dental: procedimiento de 90 minutos, evitar alimentos colorantes 24h antes",
    "Consulta de ortodoncia: 30 minutos, traer radiografías existentes si las tiene",
    "Empaste dental: 45 minutos, anestesia local, no comer hasta que pase el efecto",
    "Endodoncia: tratamiento de 90-120 minutos, puede requerir múltiples visitas",
    "Periodoncia: tratamiento de encías, 60 minutos por sesión",
    "Horario de atención: Lunes a Viernes 9:00-19:00, Sábados 9:00-13:00",
    "Ubicación: Clínica Dental Sonrisa Saludable, Av. Principal 123",
    "Emergencias dentales: atendemos el mismo día, llamar al +123456789"
]

# Reemplaza o agrega a tu colección existente
mi_coleccion.add(
    documents=documentos_odontologia,
    ids=[f"dental_doc_{i}" for i in range(len(documentos_odontologia))]
)

print("✅ Documentos guardados en la base vectorial local.")