from google.colab import userdata
from google import genai

api_key = userdata.get('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

history = []


# Puedes estar en 2 pestañas por el momento, todos jalan info de usuario e memoria contextual:
# Servicios -> jala la info de contexto de servicios y te peude devolver o hablar de servicios de la bd
# Wearables -> jala la data de historial medico (wearables)
# El contexto es que es un agente especializado en cuidado de la salud de tu usuario, no eres un doctor, no das especficaciones, pero sí peudes hacer deducciones y sugerencias basado solo en la info que jalas de la bases de datos, por ejemplo, si el usuario tiene un historial de enfermedades, puedes sugerirle que haga una consulta con un doctor.

def ask(user_input):
    history.append(f"Usuario: {user_input}")

    # Concatenamos todo el historial
    full_context = "\n".join(history) + "\nAsistente:"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_context
    )

    answer = response.text
    history.append(f"Asistente: {answer}")
    return answer

print(ask("Hola, quién eres?"))
print(ask("Qué recuerdas de lo que hablamos?"))
