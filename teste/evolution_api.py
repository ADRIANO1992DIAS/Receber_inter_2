

import os
import sys
import requests

# Permite configurar por ambiente, mantendo seus defaults atuais
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME", "evolution")
EVOLUTION_AUTHENTICATION_API_KEY = os.getenv("EVOLUTION_AUTHENTICATION_API_KEY", "sdjglokogkrW352$")

def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)

def send_whatsapp_message(number: str, text: str, timeout: int = 20) -> requests.Response:
    """
    Envia mensagem de texto via Evolution API e retorna o objeto requests.Response.
    Lança exceção se houver erro de rede/HTTP.
    """
    if not number or not text:
        fail("Parâmetros obrigatórios ausentes: 'number' e/ou 'text'.")

    url = f"{EVOLUTION_API_URL.rstrip('/')}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
    headers = {
        "apikey": EVOLUTION_AUTHENTICATION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "number": number,   # ex.: 5585XXXXXXXX (sem @c.us)
        "text": text,
    }

    # Faça o POST e levante erro para HTTP 4xx/5xx
    resp = requests.post(url=url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp

if __name__ == "__main__":
    numero = os.getenv("TEST_NUMBER", "558585134478")  # ajuste aqui
    mensagem = os.getenv("TEST_MESSAGE", "Teste_09_11_2025")

    print(f"Enviando para {numero} via {EVOLUTION_API_URL} (instância: {EVOLUTION_INSTANCE_NAME})...")
    try:
        resp = send_whatsapp_message(numero, mensagem)
    except requests.exceptions.RequestException as exc:
        fail(f"Falha ao enviar mensagem: {exc}")

    # Se chegou aqui, foi 2xx
    print(f"Mensagem enviada para {numero}. Status {resp.status_code}.")
    try:
        print("Resposta:", resp.json())
    except Exception:
        print("Resposta:", resp.text)
