from openai import OpenAI
import chromadb
import os
from dotenv import load_dotenv
from chromadb.utils import embedding_functions

# Cargar la API key
load_dotenv()
# Inicializamos el cliente de OpenAI
client = OpenAI()

# Inicializamos Chroma (por defecto guarda en .chromadb/ localmente)
chroma_client = chromadb.Client()

# Definimos una colección donde guardaremos nuestros textos
collection = chroma_client.create_collection(name="documentos_oberoende")

# Creamos la función de embeddings con OpenAI
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    #api_key="TU_API_KEY_AQUI",
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

# Textos de ejemplo (pueden ser respuestas, información de empresa, etc.)
documentos = [
    "Oberoende ofrece soluciones de chatbots conectados con WhatsApp y otras plataformas.",
    "Nuestros chatbots pueden responder preguntas frecuentes y automatizar tareas repetitivas.",
    "Implementamos integraciones personalizadas usando Twilio, Flask y APIs REST.",
    "Los modelos de lenguaje permiten mejorar la comprensión del contexto y dar respuestas más naturales."
]

# Agregamos los documentos a la colección con sus embeddings
collection.add(
    documents=documentos,
    ids=[f"doc_{i}" for i in range(len(documentos))]
)

print("✅ Documentos guardados en la base vectorial local.")

nuevo_texto = "Nuestros chatbots permiten automatizar tareas, enviar notificaciones y atender clientes 24/7."
collection.update(ids=["doc_1"], documents=[nuevo_texto])
print("✅ Documento actualizado correctamente.")

# Ahora hacemos una búsqueda semántica:
pregunta = "¿Cómo se conectan sus chatbots con WhatsApp?"
resultados = collection.query(
    query_texts=[pregunta],
    n_results=2  # cantidad de coincidencias que queremos
)

# Mostramos los resultados más similares
print("\n🔍 Resultados de la búsqueda semántica:\n")
print(resultados)
for doc, dist in zip(resultados["documents"][0], resultados["distances"][0]):
    print(f"➡️ Texto: {doc}\n   Similaridad: {1 - dist:.3f}\n")

collection.delete(ids=["doc_0"])
print("✅ Documento eliminado correctamente.")

chroma_client.delete_collection(name="documentos_oberoende")
print("✅ Colección eliminada correctamente.")