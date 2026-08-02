import os
import time
import re
import tempfile
import urllib.request
import pandas as pd
from vk_api import VkUpload
from vk_api.longpoll import VkLongPoll, VkEventType
import random

VK_TOKEN = os.getenv('VK_TOKEN')

vk_session = vk_api.VkApi(token=VK_TOKEN)
upload = VkUpload(vk_session)
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

GREETINGS = [
    "👋 Привет! Я та самая альтушка с сайта. Готова покопаться в твоих табличках! ✨",
    "👓 Привет-привет! Люблю Excel и хаос в ячейках — я его превращаю в порядок. 📊",
    "🖤 Рада видеть! Скинь файл — сделаю из него конфетку. 😊"
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

def clean_text(text):
    """Чистит текст: убирает лишние пробелы, переносы, табуляции"""
    if not isinstance(text, str):
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_year(text):
    match = re.search(r'\b(19|20)\d{2}\b', text)
    return match.group(0) if match else None

def extract_mileage(text):
    # Поддерживаем: 123456км, 123 456 км, 123456, «пробег 123456»
    # Сначала убираем пробелы внутри числа, чтобы было проще искать
    t = re.sub(r'(\d)\s+(\d)', r'\1\2', text)
    match = re.search(r'(\d{4,})\s*км', t, re.IGNORECASE)
    if match:
        return match.group(1) + ' км'
    # Если нет «км», но есть большое число — считаем его пробегом
    match_num = re.search(r'\b(\d{5,})\b', t)
    if match_num:
        return match_num.group(1) + ' км'
    return None

def extract_formular(text):
    # АД№..., БЗ№..., №..., иногда без префикса
    match = re.search(r'[А-Я]{0,3}№?\s*\d+', text)
    return match.group(0).strip() if match else None

def extract_order(text):
    match = re.search(r'наряд\s*([А-Я0-9№\-]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_cabin(text):
    # Ищем 6–7 цифр подряд — это часто код кабины
    match = re.search(r'\b\d{6,7}\b', text)
    return match.group(0) if match else None

def extract_engine(text):
    # Паттерн ДВС: 40.30-260D2693835 и похожие
    match = re.search(r'\d{2,3}\.\d{2}-\w+', text)
    return match.group(0) if match else None

def extract_driver(text):
    # Фамилия + инициалы: Иванов И.И. или Иванов И.
    match = re.search(r'[А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ]\.?[А-ЯЁ]?\.?', text)
    return match.group(0).strip() if match else None

def process_excel_file(file_path):
    df = pd.read_excel(file_path)
    rows = len(df)
    cols = len(df.columns)

    # Находим текстовые колонки с длинными значениями — кандидаты на разбор
    candidate_cols = []
    for c in df.columns:
        if df[c].dtype == 'object':
            sample = df[c].dropna().head(5)
            if len(sample) > 0 and any(len(str(x)) > 40 for x in sample):
                candidate_cols.append(c)

    report = (
        f"📘 Файл обработан! 🎉\n\n"
        f"Строк: {rows}\n"
        f"Колонок: {cols}\n\n"
    )

    if not candidate_cols:
        report += (
            "🔍 Не нашла «длинных» текстовых колонок для разбора.\n"
            "Если хочешь разобрать конкретную колонку — напиши её название, я добавлю правило! 💛\n"
        )
        return report, df

    report += f"🎯 Кандидаты на разбор: {', '.join(candidate_cols)}\n\n"

    # Будем разбирать первую найденную колонку-кандидат
    target_col = candidate_cols[0]
    report += f"✨ Начинаю разбор колонки: '{target_col}'…\n\n"

    # Создаём новые колонки
    new_cols = ['ГОД', 'ПРОБЕГ', 'ФОРМУЛЯР', 'НАРЯД', 'КАБИНА', 'ДВС', 'ВОДИТЕЛЬ']
    for nc in new_cols:
        df[nc] = None

    parsed_count = 0
    for i, row in df.iterrows():
        text = clean_text(str(row[target_col]))
        if not text:
            continue

        year = extract_year(text)
        mileage = extract_mileage(text)
        formular = extract_formular(text)
        order = extract_order(text)
        cabin = extract_cabin(text)
        engine = extract_engine(text)
        driver = extract_driver(text)

        # Заполняем строку
        if year:
            df.at[i, 'ГОД'] = year
        if mileage:
            df.at[i, 'ПРОБЕГ'] = mileage
        if formular:
            df.at[i, 'ФОРМУЛЯР'] = formular
        if order:
            df.at[i, 'НАРЯД'] = order
        if cabin:
            df.at[i, 'КАБИНА'] = cabin
        if engine:
            df.at[i, 'ДВС'] = engine
        if driver:
            df.at[i, 'ВОДИТЕЛЬ'] = driver

        if any([year, mileage, formular, order, cabin, engine, driver]):
            parsed_count += 1

    report += (
        f"✅ Удалось разобрать: {parsed_count} из {rows} строк.\n\n"
        f"✨ Теперь у тебя есть аккуратные колонки: {', '.join(new_cols)}.\n"
    )

    # Сводная по годам (если есть ГОД)
    if df['ГОД'].notna().any():
        year_summary = df.groupby('ГОД').size().reset_index(name='Количество строк')
        report += "🗓 Сводка по годам:\n"
        for _, r in year_summary.iterrows():
            report += f"   • {r['ГОД']}: {r['Количество строк']} строк\n"
        report += "\n"

    # Суммарный пробег (если есть ПРОБЕГ)
    if df['ПРОБЕГ'].notna().any():
        # Извлекаем число из «123456 км»
        def to_num(x):
            if not x:
                return None
            m = re.search(r'(\d+)', str(x))
            return int(m.group(1)) if m else None
        nums = df['ПРОБЕГ'].apply(to_num)
        total_km = nums.sum()
        report += f"🚗 Суммарный пробег: {total_km:,.0f} км\n\n"

    report += (
        "💡 Если формат данных чуть другой — скажи, я подстрою правила!\n"
        "А ещё я могу прислать обратно готовый Excel с новыми колонками. ✨"
    )
    return report, df

def upload_excel_to_vk(user_id, df, filename="processed_data.xlsx"):
    """Сохраняет DataFrame в Excel, загружает в VK как документ и возвращает attachment"""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        df.to_excel(tmp_path, index=False)
        doc_info = upload.doc(tmp_path, title=filename, peer_id=user_id)
        attachment = f"doc{doc_info['owner_id']}_{doc_info['id']}"
        return attachment
    except Exception as e:
        print("Ошибка загрузки файла:", e)
        return None
    finally:
        try:
            os.remove(tmp_path)
        except:
            pass
def upload_photo(file_path):
    """Загружает фото в сообщения и возвращает attachment"""
    photo = upload.photo_messages(photos=file_path)[0]
    attachment = f"photo{photo['owner_id']}_{photo['id']}"
    return attachment

def upload_video(file_path):
    """Загружает видео в сообщения и возвращает attachment"""
    video = upload.video_messages(file_path=file_path)
    attachment = f"video{video['owner_id']}_{video['id']}"
    return attachment
    
def send_typing(user_id):
    """Просит VK показать статус «печатает…» у бота"""
    try:
        vk_session.method('messages.setActivity', {
            'user_id': user_id,
            'type': 'typing'
        })
    except Exception:
        pass  # Если не сработает в каком-то клиенте — не страшно

def upload_photo(file_path):
    photo = upload.photo_messages(photos=file_path)[0]
    return f"photo{photo['owner_id']}_{photo['id']}"

def upload_video(file_path):
    video = upload.video_messages(file_path=file_path)
    return f"video{video['owner_id']}_{video['id']}"

# Основной цикл
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_id = event.user_id
        text = event.text.strip() if event.text else ""
        attachments = event.attachments

        has_doc = False
        has_photo = False
        has_video = False

        # Сначала определяем типы вложений
        for att in attachments:
            t = att.get('type')
            if t == 'doc':
                has_doc = True
            elif t == 'photo':
                has_photo = True
            elif t == 'video':
                has_video = True

        # Приоритет: сначала doc (Excel), потом фото, потом видео, потом текст
        if has_doc:
            for att in attachments:
                if att.get('type') != 'doc':
                    continue
                doc = att['doc']
                file_url = doc['url']
                file_ext = doc.get('ext', '').lower()

                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                        tmp_path = tmp.name
                    urllib.request.urlretrieve(file_url, tmp_path)

                    # Эффект «печатает…»
                    send_typing(user_id)
                    time.sleep(random.randint(1, 3))
                    send_message(user_id, get_thinking())

                    if file_ext in ['xlsx', 'xls']:
                        report, df_processed = process_excel_file(tmp_path)
                        send_message(user_id, report)

                        attachment = upload_excel_to_vk(user_id, df_processed)
                        if attachment:
                            send_message(
                                user_id,
                                "📎 Вот твой готовый файл с разбитыми колонками! Скачивай и пользуйся. ✨",
                                attachment=attachment
                            )
                        else:
                            send_message(user_id, "⚠️ Не удалось отправить файл обратно, но данные уже обработаны — можешь сохранить отчёт.")
                    else:
                        send_message(user_id, f"📄 Принял файл ({file_ext}), но пока лучше всего умею работать с Excel. Если это CSV — скажи, тоже помогу! ✨")
                except Exception as e:
                    send_message(user_id, f"❌ Ой, не получилось скачать файл. Попробуй ещё раз. 😕 Ошибка: {str(e)[:120]}")

        elif has_photo:
            # Бот «печатает» и отвечает про фото
            send_typing(user_id)
            time.sleep(1)
            send_message(user_id, "📸 Фото получено! Пока просто радуюсь картинке. Если скажешь, что с ним делать — придумаю магию! ✨")
            # Тут позже можно добавить: скачать фото, сохранить, отправить в нейросеть и т.п.

        elif has_video:
            send_typing(user_id)
            time.sleep(1)
            send_message(user_id, "🎥 Видео получено! Сейчас не умею его обрабатывать, но могу сохранить или переслать. Скажи, что нужно! ✨")

        else:
            # Обычные текстовые сообщения
            text_low = text.lower()
            if any(w in text_low for w in ['привет', 'здравствуй', 'хай']):
                send_message(user_id, get_greeting())
            elif any(w in text_low for w in ['пока', 'до свидания']):
                send_message(user_id, "👋 Пока-пока! Если что — я тут, с табличками наготове. 💖")
            else:
                send_message(user_id, (
                    "🤔 Интересный вопрос! Хочешь, разберу Excel? Просто скинь файл — я сделаю разбивку на ГОД/ПРОБЕГ/ФОРМУЛЯР и т.д., посчитаю сводку и верну готовый файл.\n"
                    "Или пришли фото/видео — пока просто порадуюсь, а дальше придумаем! ✨"
                ))
