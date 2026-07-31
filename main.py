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
