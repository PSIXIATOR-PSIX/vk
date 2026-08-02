from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Вставь сюда тот же ключ, который будешь использовать в настройках группы VK
VK_SECRET_KEY = "my_super_secret_key_123"

class VKCallback(BaseModel):
    type: str
    group_id: int
    secret: str | None = None
    message: dict | None = None

@app.get("/")
async def root():
    return {"message": "Сервер на Render работает. Бот готов."}

@app.post("/vk-callback")
async def vk_callback(request: Request, data: VKCallback):
    # 1. Подтверждение сервера: VK требует вернуть строку
    if data.type == "confirmation":
        return VK_SECRET_KEY

    # 2. Проверка ключа: защита от подделок
    if data.secret != VK_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid secret key")

    # 3. Обработка нового сообщения
    if data.type == "message_new":
        user_id = data.message.get("from_id")
        text = data.message.get("text", "")
        print(f"Новое сообщение от пользователя {user_id}: {text}")

        # Здесь ты можешь добавить свою логику: запись в БД, отправку уведомлений и т.д.
        # Но сам ответ пользователю делается отдельным запросом к VK API (messages.send)
        return {"status": "ok"}

    return {"status": "ok"}
    return {"status": "ok"}
    import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import openai  # pip install openai

# --- НАСТРОЙКИ ---
VK_TOKEN = os.getenv('VK_TOKEN')  # возьми из переменных окружения Render
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # тоже из Render

# Инициализация VK
vk_session = vk_api.VkApi(token=VK_TOKEN)
longpoll = VkLongPoll(vk_session)

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def send_message(user_id, text):
    vk_session.method('messages.send', {
        'user_id': user_id,
        'message': text,
        'random_id': 0
    })

def get_ai_response(user_text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты — дружелюбный мультяшный бот-альтушка. Отвечай кратко, с эмодзи, в лёгком стиле, но по делу. Не использу длинные вступления."},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7,
            max_tokens=256
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Ошибка AI:", e)
        return "Ой, сейчас не могу поболтать — сервер думает. Попробуй ещё раз!"

# Основной цикл
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_text = event.text.strip()
        if not user_text:
            continue
        
        # Отправляем «печатает…» (опционально)
        # Тут можно добавить статус typing, если нужно
        
        ai_text = get_ai_response(user_text)
        send_message(event.user_id, ai_text)

