from google.colab import userdata
from google import genai

api_key = userdata.get('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

history = []

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
