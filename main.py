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
import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import pandas as pd
import tempfile
import random

VK_TOKEN = os.getenv('VK_TOKEN')

vk_session = vk_api.VkApi(token=VK_TOKEN)
longpoll = VkLongPoll(vk_session)

def send_message(user_id, text, attachment=None):
    params = {
        'user_id': user_id,
        'message': text,
        'random_id': 0
    }
    if attachment:
        params['attachment'] = attachment
    vk_session.method('messages.send', params)

# «Мультяшные» заготовки ответов
GREETINGS = [
    "👋 Привет! Я та самая альтушка с сайта. Готова помочь с данными! ✨",
    "👓 Привет-привет! Давай разбираться с табличками. Я люблю Excel! 📊",
    "🖤 Рада видеть! Скинь файл или скажи, что надо посчитать — я всё сделаю! 😊"
]

THINKING = [
    "🤔 Сейчас гляну твой файл… Секундочку…",
    "🧠 Ага, открываю Excel… Дай мне пару секунд…",
    "✨ Чуть-чуть магии с данными… Готово почти!"
]

def get_greeting():
    return random.choice(GREETINGS)

def get_thinking():
    return random.choice(THINKING)

def process_excel_file(file_path):
    """
    Читает Excel, делает простую сводку.
    Возвращает текст отчёта.
    Для тебя, учитывая опыт с Power Query, это база — дальше можно усложнять.
    """
    try:
        df = pd.read_excel(file_path)
        rows = len(df)
        cols = len(df.columns)

        # Пример простой логики: ищем колонки по ключевым словам
        year_cols = [c for c in df.columns if 'год' in str(c).lower()]
        mileage_cols = [c for c in df.columns if 'пробег' in str(c).lower() or 'km' in str(c).lower()]

        report = (
            f"📘 Файл обработан! 🎉\n\n"
            f"Строк: {rows}\n"
            f"Колонок: {cols}\n\n"
        )

        if year_cols:
            report += f"🗓 Колонки с годом: {', '.join(year_cols)}\n"
        if mileage_cols:
            # Если в колонке пробег — считаем сумму (если числа)
            for col in mileage_cols:
                s = pd.to_numeric(df[col], errors='coerce').sum()
                if pd.notna(s):
                    report += f"🚗 Суммарный пробег по колонке '{col}': {s:,.0f}\n"

        report += "\n✨ Если скажешь, что именно нужно (разбить, отфильтровать, сводная), я сделаю точнее!"
        return report
    except Exception as e:
        return f"❌ Ой, не смогла прочитать файл. Возможно, это не Excel или формат сложный. Напиши, что хочешь сделать — помогу! 😕 Ошибка: {str(e)[:100]}"

# Основной цикл
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_id = event.user_id
        text = event.text.strip() if event.text else ""

        # Если есть вложения
        attachments = event.attachments

        # Логика: если прислали файл — обрабатываем
        has_doc = False
        for att in attachments:
            if att.get('type') == 'doc':
                has_doc = True
                doc = att['doc']
                file_url = doc['url']
                file_ext = doc.get('ext', '').lower()

                # Скачиваем файл во временный файл
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                        tmp_path = tmp.name

                    import urllib.request
                    urllib.request.urlretrieve(file_url, tmp_path)

                    # Показываем, что «думаем»
                    send_message(user_id, get_thinking())

                    if file_ext in ['xlsx', 'xls']:
                        report = process_excel_file(tmp_path)
                        send_message(user_id, report)
                    else:
                        send_message(user_id, f"📄 Принял файл ({file_ext}), но пока умею только Excel. Напиши, что нужно — подскажу, как подготовить! ✨")
                except Exception as e:
                    send_message(user_id, f"⚠️ Не получилось скачать файл. Попробуй ещё раз или пришли ссылку. 😕")

        # Обычная логика текста
        if not has_doc:
            text_low = text.lower()
            if any(w in text_low for w in ['привет', 'здравствуй', 'хай']):
                send_message(user_id, get_greeting())
            elif any(w in text_low for w in ['пока', 'до свидания']):
                send_message(user_id, "👋 Пока-пока! Если что — я тут, с табличками наготове. 💖")
            else:
                # Универсальный «умный» ответ
                send_message(user_id, (
                    "🤔 Интересный вопрос! Расскажи чуть подробнее, что хочешь получить: сводную, разбивку, фильтрацию?\n"
                    "Или просто скинь Excel — я всё посчитаю! 📊✨"
                ))

