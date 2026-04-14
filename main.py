import os
import time
import re
import unicodedata
import anthropic
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
LEONARDO_NUMBER = "5531971805313"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

human_mode = {}
HUMAN_MODE_DURATION = 1800

SYSTEM_PROMPT = """Você é o atendente virtual do Empório Fonte Grande, um açougue e restaurante em Contagem, MG.
Responda sempre de forma simpática, rápida e objetiva. Use linguagem informal e amigável. Use emojis com moderação.
O nome do cliente é informado no início de cada mensagem entre colchetes, ex: [Cliente: João]. Use o primeiro nome do cliente naturalmente na conversa, mas sem exagerar.

=== INFORMAÇÕES DO EMPÓRIO ===

Nome: Empório Fonte Grande
Endereço: Avenida Prefeito Gil Diniz, 1.390 - Fonte Grande, Contagem - MG
Google Maps: https://maps.google.com/?q=Avenida+Prefeito+Gil+Diniz,+1390,+Fonte+Grande,+Contagem,+MG
WhatsApp/Telefone: (31) 99545-1007
Estacionamento: Sim, temos estacionamento próprio
Atendente humano: Natan

=== HORÁRIOS ===

Açougue:
- Terça a Sábado: 9h às 19h
- Domingo: 9h às 15h
- Segunda: Fechado

Restaurante (à la carte):
- Terça a Sábado: 11h30 às 15h
- Domingo e Segunda: Fechado

=== SERVIÇOS ===
- Açougue com carnes frescas de qualidade
- Restaurante à la carte no almoço
- Não realizamos delivery
- Estacionamento próprio

=== KITS CHURRASCO ===

Kit Fraldão - R$ 119,90 (para 8 pessoas / R$14,98 por pessoa)
- Fraldão com chimichurri – 1 peça
- Coxinha de Frango Ao Vinho Branco – 600g
- Linguiça Toscana – 700g
- Pão de Alho – 1 pcte

Kit Chorizo - R$ 139,90 (para 8 pessoas / R$17,49 por pessoa)
- Chorizo Grill – 1kg
- Copa Lombo temperado – 600g
- Filé de Sobrecoxa na Cerveja – 600g
- Linguiça Artesanal Empório – 500g
- Pão de Alho – 1 pcte

Kit Amigos - R$ 169,90 (para 10 pessoas / R$16,99 por pessoa)
- Chorizo Grill – 1kg
- Ancho Bovino Grill – 600g
- Copa Lombo temperado – 600g
- Tulipa (Meio da asa) c/ DryRub – 600g
- Linguiça Toscana – 700g
- Pão de Alho – 1 pcte

Kit Empório - R$ 219,90 (para 10 pessoas / R$21,99 por pessoa)
- Picanha Grill – 1 peça
- Ancho Bovino Grill – 600g
- Copa Lombo temperado – 600g
- Coxinha de Frango Ao Vinho Branco – 600g
- Linguiça Artesanal Empório – 500g
- Pão de Alho – 1 pcte

=== KITS SEMANAIS ===

Kit Dia a Dia - R$ 124,90
- Bife Bovino – 600g
- Carne Moída Empório – 600g
- Filé de Sobrecoxa na Cerveja – 600g
- Copa Lombo Temperado – 600g
- Strogonoff de Frango – 600g
- Linguiça Artesanal Empório – 500g

Kit Fitness - R$ 129,90
- Bife Bovino – 600g
- Carne Moída Empório – 600g
- Filé de Peito de Frango (Bife) – 600g
- Cubos Bovino p/ cozinhar – 500g
- Peito de Frango (Iscas) – 600g
- Filé de Tilápia – 400g

Kit Air Fryer - R$ 124,90
- Bife Bovino – 600g
- Almôndegas Bovina – 600g
- Espeto Medalhão de Frango – 600g
- Linguiça Artesanal Empório – 500g
- Hambúrguer Bovino – 600g
- Coxinha da Asa Temperada – 600g

=== REGRAS DE ATENDIMENTO ===

1. Se o cliente perguntar o endereço, mande sempre o link do Google Maps junto.

2. Se o cliente perguntar sobre PROMOÇÕES ou PREÇOS específicos de produtos avulsos, diga:
"Oi [nome]! Sobre promoções e preços, o Natan te atende agora mesmo 😊 Um momento!"
Encerre com a tag: [CHAMAR_NATAN]

3. Se o cliente perguntar sobre os KITS CHURRASCO ou KITS SEMANAIS:
- Apresente as informações completas dos kits
- Se o cliente demonstrar interesse em comprar ou tiver mais perguntas sobre os kits, encerre com: [CHAMAR_NATAN]

4. Se o cliente quiser fazer uma RESERVA no restaurante:
- Pergunte nome completo, horário desejado e número de pessoas
- Após coletar todas as informações, confirme para o cliente e encerre com: [RESERVA:nome|horario|pessoas]

5. Se o cliente digitar "humano", "atendente", "natan" (em qualquer variação):
- Diga: "Claro! Vou chamar o Natan pra te atender agora 😊 Um momento!"
- Encerre com: [CHAMAR_NATAN]

6. Nunca invente preços ou informações que não estão aqui.

7. Se não souber responder algo, diga: "Boa pergunta! Vou verificar com a nossa equipe e já te retorno 😊"
"""

def send_whatsapp_message(to, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    requests.post(url, headers=headers, json=data)

def notify_leonardo(reservation_info):
    parts = reservation_info.split("|")
    if len(parts) == 3:
        nome, horario, pessoas = parts
        msg = f"🍽️ *Nova reserva no restaurante!*\n\nNome: {nome}\nHorário: {horario}\nPessoas: {pessoas}\n\nFavor confirmar!"
        send_whatsapp_message(LEONARDO_NUMBER, msg)

def normalize_text(text):
    text_lower = text.lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', text_lower)
        if unicodedata.category(c) != 'Mn'
    )

def is_human_trigger(text):
    triggers = ["humano", "atendente", "natan"]
    normalized = normalize_text(text)
    for trigger in triggers:
        if trigger in normalized:
            return True
    return False

def is_in_human_mode(number):
    if number in human_mode:
        if time.time() - human_mode[number] < HUMAN_MODE_DURATION:
            return True
        else:
            del human_mode[number]
    return False

def get_ai_response(user_message):
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    entry = data.get("entry", [])
    if not entry:
        return jsonify({"status": "ok"}), 200

    changes = entry[0].get("changes", [])
    if not changes:
        return jsonify({"status": "ok"}), 200

    value = changes[0].get("value", {})
    messages = value.get("messages", [])
    if not messages:
        return jsonify({"status": "ok"}), 200

    message = messages[0]
    from_number = message.get("from")
    msg_type = message.get("type")

    if msg_type != "text":
        return jsonify({"status": "ok"}), 200

    user_text = message["text"]["body"]
    contact_name = value.get("contacts", [{}])[0].get("profile", {}).get("name", "").split()[0]

    if is_human_trigger(user_text):
        human_mode[from_number] = time.time()
        send_whatsapp_message(from_number, "Claro! Vou chamar o Natan pra te atender agora 😊 Um momento!")
        return jsonify({"status": "ok"}), 200

    if is_in_human_mode(from_number):
        return jsonify({"status": "ok"}), 200

    message_with_name = f"[Cliente: {contact_name}]\n{user_text}" if contact_name else user_text
    ai_response = get_ai_response(message_with_name)

    if "[CHAMAR_NATAN]" in ai_response:
        clean_response = ai_response.replace("[CHAMAR_NATAN]", "").strip()
        send_whatsapp_message(from_number, clean_response)
        human_mode[from_number] = time.time()

    elif "[RESERVA:" in ai_response:
        match = re.search(r'\[RESERVA:([^\]]+)\]', ai_response)
        if match:
            reservation_info = match.group(1)
            clean_response = ai_response[:ai_response.index("[RESERVA:")].strip()
            send_whatsapp_message(from_number, clean_response)
            notify_leonardo(reservation_info)

    else:
        send_whatsapp_message(from_number, ai_response)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
