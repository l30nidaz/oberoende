from openai import OpenAI
import numpy as np
import os
from dotenv import load_dotenv

# Cargar la API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    print(a)
    print(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Ejemplo práctico
text1 = "precio del plan premium"
text2 = "cuánto cuesta el plan avanzado"
text3 = "horarios de atención al cliente"

embed1 = get_embedding(text1)
embed2 = get_embedding(text2)
embed3 = get_embedding(text3)

print("Similitud entre texto 1 y 2:", cosine_similarity(embed1, embed2))
print("Similitud entre texto 1 y 3:", cosine_similarity(embed1, embed3))
