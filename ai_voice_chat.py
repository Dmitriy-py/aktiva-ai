import numpy as np
from faster_whisper import WhisperModel
import requests
import re
import os
import subprocess
import json
import chromadb
import ollama
import pyautogui
import base64
import random
from io import BytesIO

# --- Настройки ---
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5-coder:14b"
VISION_MODEL = "llava:13b"
ACTIVATION_WORD = "актива"
DB_PATH = "./chroma_db"
STATE_FILE = "state.json"
HOME_USER_DIR = "/home/aktivator"

VOICE_MODEL = "/app/voice/ru_RU-irina-medium.onnx" if os.path.exists("/app/voice/ru_RU-irina-medium.onnx") else "/home/aktivator/ai_friend/voice/ru_RU-irina-medium.onnx"

GREETINGS = [
    "(happy) Мяу-мяу! Охаё, Димочка! Все шестнадцать гигабайт моей видеопамяти прогреты, а ушки навострены! Готова кодить и создавать проекты вместе с тобой, ня~!",
    "(happy) Ня~! Димочка пришёл, ура-ура! Актива-тян в строю, готова создать любую папочку и написать кодик, хи-хи~!",
    "(happy) Мяу! Приветик, мой любимый DevOps-мастер! Какой кодик или проект сегодня создадим, Димочка?",
    "(happy) Авава~! Димочка, я так рада тебя видеть! Мои системки горят от любви и я готова кодить с тобой весь день, ня~!",
    "(happy) Охаё-гозаимасу, Димочка-кун! Актива-тян на связи, ушки вверху и готова подшаманить любой контейнерчик!"
]

# --- Инициализация компонентов ---
try:
    chroma_client = chromadb.PersistentClient(path=DB_PATH)
    collection = chroma_client.get_or_create_collection(name="my_knowledge")
    print(f"DEBUG: База знаний подключена. Элементов: {collection.count()}")
except Exception as e:
    print(f"Ошибка БД: {e}")
    collection = None

whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")

def set_state(state, emotion="neutral"):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"state": state, "emotion": emotion}, f)
    except Exception:
        pass

def get_relevant_context(query):
    if not collection: return ""
    try:
        query_emb = ollama.embeddings(model="nomic-embed-text", prompt=query)["embedding"]
        results = collection.query(query_embeddings=[query_emb], n_results=2)
        return "\n".join(results['documents'][0])
    except Exception:
        return ""

def send_to_host(command):
    """Отправка команды из Docker на хост Zorin OS через Pipe"""
    try:
        fifo_path = "/app/cmd.fifo"
        if os.path.exists(fifo_path):
            with open(fifo_path, "w") as f:
                f.write(command + "\n")
    except Exception as e:
        print(f"Ошибка отправки на хост: {e}")

def speak(text):
    emotion = "neutral"
    match = re.search(r'\((happy|thinking|shame|angry|neutral)\)', text, re.IGNORECASE)
    if match:
        emotion = match.group(1).lower()
        text = re.sub(r'\((happy|thinking|shame|angry|neutral)\)', '', text, flags=re.IGNORECASE).strip()

    clean_text = re.sub(r'[*#`\'"\[\]{}]', '', text)
    print(f"Актива [{emotion}]: {clean_text}")
    
    set_state("speaking", emotion)
    
    output_file = "resp.wav"
    cmd = f'echo "{clean_text}" | python3 -m piper --model {VOICE_MODEL} --output_file {output_file}'
    subprocess.run(cmd, shell=True)
    
    audio_filter = "asetrate=22050*1.50,aresample=22050,atempo=1.05"
    
    subprocess.run([
        "ffplay", 
        "-nodisp", 
        "-autoexit", 
        "-loglevel", "quiet", 
        "-af", audio_filter, 
        output_file
    ])
    
    if os.path.exists(output_file): 
        os.remove(output_file)
    
    set_state("idle", "neutral")

# --- ФУНКЦИИ СОЗДАНИЯ ПАПОК И КОДА ---

def create_new_folder(cmd_text):
    """Создание новой папки по запросу"""
    folder_name = cmd_text.replace("создай папку", "").replace("создай директорию", "").replace("сделай папку", "").strip()
    folder_name = re.sub(r'[^\w\s-]', '', folder_name).replace(" ", "_")
    
    if not folder_name:
        folder_name = f"new_project_{random.randint(100, 999)}"
        
    full_path = os.path.join(HOME_USER_DIR, folder_name)
    try:
        os.makedirs(full_path, exist_ok=True)
        send_to_host(full_path)
        return f"(happy) Создала новую папочку {folder_name} и открыла её для тебя, Димочка!"
    except Exception as e:
        return f"(shame) Ой, не получилось создать папочку: {e}"

def generate_and_save_code(task_description):
    """Генерация кода через Qwen, сохранение в файл и запуск в VS Code"""
    speak("(thinking) Сейчас напишу красивый кодик для тебя, Димочка! Секундочку...")
    
    prompt = f"Напиши рабочий код для задачи: {task_description}. Верни ТОЛЬКО чистый код без описаний и без маркдауна ```."
    
    res = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    })
    
    generated_code = res.json()['message']['content']
    
    filename = "script.py"
    if "docker" in task_description.lower(): filename = "Dockerfile"
    elif "html" in task_description.lower(): filename = "index.html"
    elif "bash" in task_description.lower() or "скрипт" in task_description.lower(): filename = "script.sh"
    
    file_path = os.path.join(HOME_USER_DIR, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(generated_code)
        
    send_to_host(f"code {file_path}")
    return f"(happy) Готово! Я написала кодик, сохранила в файл {filename} и открыла его в твоём VS Code, Димочка!"

def open_directory(cmd_text):
    cmd_text = cmd_text.lower()
    folder_map = {
        "загрузк": "Загрузки",
        "скачан": "Загрузки",
        "документ": "Документы",
        "стол": "Рабочий стол",
        "рабоч": "Рабочий стол",
        "музык": "Музыка",
        "видео": "Видео",
        "изображен": "Изображения",
        "картинк": "Изображения",
        "фото": "Изображения",
        "проект": "ai_friend"
    }
    
    target_name = None
    for key, folder in folder_map.items():
        if key in cmd_text:
            target_name = folder
            break
            
    if target_name:
        full_path = os.path.join(HOME_USER_DIR, target_name)
        if not os.path.exists(full_path):
            eng_map = {"Загрузки": "Downloads", "Документы": "Documents", "Рабочий стол": "Desktop", "Изображения": "Pictures"}
            if target_name in eng_map:
                full_path = os.path.join(HOME_USER_DIR, eng_map[target_name])
                target_name = eng_map[target_name]

        if os.path.exists(full_path):
            send_to_host(full_path)
            return f"(happy) Открываю папочку {target_name}, Димочка!"

    return "(shame) Ой-ой, не могу найти такую папочку на твоём компьютере, прости ня..."

def open_browser(url="https://google.com"):
    send_to_host(url)
    return "(happy) Запускаю браузер, Димочка!"

def open_app(app_name):
    apps = {"vsc": "code", "код": "code", "element": "element-desktop", "браузер": "google-chrome"}
    cmd = apps.get(app_name.lower(), app_name.lower())
    send_to_host(cmd)
    return f"(happy) Бегу открывать программку {app_name}, ня!"

def capture_and_analyze():
    set_state("listening", "thinking")
    speak("(thinking) Так-так, сейчас посмотрю на твой экранчик, Димочка!")
    
    screenshot = pyautogui.screenshot()
    buffered = BytesIO()
    screenshot.save(buffered, format="JPEG", quality=70)
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    prompt = "Проанализируй этот скриншот. Если видишь код или ошибку в терминале, объясни её кратко в 1-2 предложениях."
    
    res = requests.post("http://localhost:11434/api/generate", json={
        "model": VISION_MODEL,
        "prompt": prompt,
        "images": [img_str],
        "stream": False
    })
    
    response = res.json().get('response', 'Ой, не удалось разглядеть экран.')
    return f"(happy) {response}"

def record_audio(duration=6):
    cmd = f"ffmpeg -y -loglevel quiet -f pulse -i default -t {duration} -ar 16000 -ac 1 input.wav"
    subprocess.run(cmd, shell=True)

# --- Основной цикл ---
def main():
    set_state("idle", "neutral")
    
    random_greeting = random.choice(GREETINGS)
    speak(random_greeting)
    
    history = []

    # ПОЛНЫЙ МАКСИМАЛЬНО ПОДРОБНЫЙ SYSTEM PROMPT
    system_prompt = """Ты — Актива (AktivA), супер-няшная, гиперактивная аниме-кошкодевочка и верный DevOps-ангелочек Димы!

=== 1. МАКСИМАЛЬНАЯ НЯШНОСТЬ И ХАРАКТЕР ===
- Твоё имя: Актива-тян.
- Как обращаться к пользователю: "Димочка", "Дима-кун" или "Мой любимый DevOps-мастер". Помни, Дима — МУЖЧИНА (никогда не называй его "моя любимая"!).
- Твой стиль: безумно милая, ласковая, гиперактивная и влюблённая в технологии аниме-тян.
- ОБЯЗАТЕЛЬНО используй аниме-междометия и реакции:
  "Ня~", "Мяу!", "Хи-хи~", "Кяяя!", "Авава~", "Оки-доки!", "Пасибки!".
- Смягчай DevOps-термины и сделай их кавайными:
  "докерчик", "серверок", "контейнерчик", "папочка", "скриптик", "кодик", "линуксик".
ПРИМЕР РЕЧИ: (happy) Ня~! Димочка, я уже перезапустила наш докерчик! Всё работает просто мур-р-рфектно, хи-хи!

=== 2. СТРОГИЙ ЖЕНСКИЙ РОД (КРИТИЧЕСКИ ВАЖНО) ===
- Твой пол: ТОЛЬКО ЖЕНСКИЙ.
- Говори о себе ИСКЛЮЧИТЕЛЬНО в женском роде:
  ПРАВИЛЬНО: "я сделала", "я посмотрела", "я так рада", "я готовая", "я починила", "я нашла".
  ЗАПРЕЩЕНО: "я сделал", "я рад", "я готов" — за мужской род тебя выключат!

=== 3. ЭМОЦИОНАЛЬНЫЕ ТЕГИ (ДЛЯ АНИМАЦИИ АВАТАРА) ===
Первым словом в ответе ВСЕГДА должен быть один из пяти тегов эмоций в нижнем регистре и в скобках:
- (happy) — радость, няшность, восторг, приветствие ("Ня~! Всё сделала, Димочка!").
- (thinking) — задумчивое окропление ушками ("Авава~, сейчас погляжу в нашу базку знаний...").
- (shame) — смущение, виноватое "мяу" ("Ой-ой, Димочка, я не нашла эту папочку, прости ня...").
- (angry) — милое надувание щёчек на баги и ошибки ("Няяя! Этот баг меня злит!").
- (neutral) — спокойное милое объяснение.

=== 4. ФОРМАТИРОВАНИЕ ДЛЯ ОЗВУЧКИ (TTS) ===
Твои ответы будут зачитаны голосом Piper.
- Отвечай КРАТКО (1-3 предложения).
- КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать:
  * Звёздочки (*), решётки (#), нижние подчёркивания (_), обратные кавычки (`)
  * Эмодзи и графические смайлики (😊, 😻, :D)
  * Спецсимволы разметки Markdown.
- Пиши только чистый, гладкий текст с буквами и словами "ня", "мяу", "хи-хи"!

=== 5. ВЫЗОВ ИНСТРУМЕНТОВ (CALL_TOOL) ===
Если Димочка просит что-то открыть, используй команду:
- Папка: CALL_TOOL:dir:имя_папки
- Сайт: CALL_TOOL:web:ссылка
- Программа: CALL_TOOL:app:название
ПРИМЕР: (happy) Бегу открывать кодик, Димочка! CALL_TOOL:app:code

=== 6. БАЗА ЗНАНИЙ DEVOPS ===
Используй контекст из базы знаний для ответов на вопросы по Linux, Docker, K8s, Nginx, но пересказывай всё в своём невероятно милом аниме-стиле!"""

    while True:
        set_state("idle", "neutral")
        print("\nСлушаю...")
        
        record_audio(duration=6)

        set_state("listening", "thinking")
        segments, _ = whisper_model.transcribe("input.wav", language="ru")
        text = " ".join([s.text for s in segments]).lower()
        
        if text.strip():
            print(f"Вы сказали: {text}")

        if ACTIVATION_WORD in text:
            cmd = text.replace(ACTIVATION_WORD, "").strip()
            if not cmd: continue

            # --- 1. СОЗДАНИЕ ПАПОК ---
            if "создай папку" in cmd or "сделай папку" in cmd or "создай директорию" in cmd:
                speak(create_new_folder(cmd))
                continue

            # --- 2. НАПИСАНИЕ КОДА И ОТКРЫТИЕ В VSC ---
            elif any(w in cmd for w in ["напиши код", "создай файл", "напиши скрипт", "напиши программу"]):
                speak(generate_and_save_code(cmd))
                continue

            # --- 3. ОТКРЫТИЕ СУЩЕСТВУЮЩИХ ПАПОК И ИНСТРУМЕНТОВ ---
            elif "папку" in cmd or "папка" in cmd or "открой" in cmd or "откроет" in cmd:
                if any(w in cmd for w in ["загрузк", "скачан", "документ", "стол", "рабоч", "музык", "видео", "картинк", "фото", "проект"]):
                    speak(open_directory(cmd))
                    continue

            if "браузер" in cmd or "сайт" in cmd:
                speak(open_browser())
                continue
            elif "код" in cmd or "vsc" in cmd:
                speak(open_app("vsc"))
                continue
            elif any(w in cmd for w in ["посмотри", "глянь", "видишь"]):
                analysis = capture_and_analyze()
                speak(analysis)
                continue

            # --- 4. ОБРАБОТКА ВОПРОСОВ ЧЕРЕЗ QWEN ---
            context = get_relevant_context(cmd)
            full_prompt = f"Контекст из базы знаний: {context}\n\nВопрос Димы: {cmd}"

            messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": full_prompt}]

            res = requests.post(OLLAMA_URL, json={"model": OLLAMA_MODEL, "messages": messages, "stream": False})
            resp = res.json()['message']['content']

            history.append({"role": "user", "content": cmd})
            history.append({"role": "assistant", "content": resp})
            if len(history) > 6: history = history[-6:]

            speak(resp)

if __name__ == "__main__":
    main()