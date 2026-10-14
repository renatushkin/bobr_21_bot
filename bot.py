import os
import time
import random
import sqlite3

import requests
from dotenv import load_dotenv
from rag import answer_question

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.getenv("MAX_BOT_TOKEN")
API = "https://platform-api2.max.ru"
CA_BUNDLE = os.path.join(BASE_DIR, "max-root-ca.crt")
DB_PATH = os.path.join(BASE_DIR, "bobr21.db")

if not TOKEN or TOKEN == "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН":
    raise RuntimeError("Проверь MAX_BOT_TOKEN в файле .env")

if not os.path.isfile(CA_BUNDLE):
    raise FileNotFoundError(
        f"Не найден сертификат: {CA_BUNDLE}"
    )

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
}

MEMES = {
    "werter": [
        "🦫 Вертер проверяет проект. Ты проверяешь вертер. "
        "Вертер проверяет твоё терпение.",
        "Проект отправлен. Теперь главное — не обновлять "
        "страницу каждые три секунды. Хотя кто мы такие, чтобы запрещать?",
        "Когда локально всё идеально, а вертер решил устроить квест.",
    ],
    "norminette": [
        "Norminette нашла лишний пробел. Код работает, "
        "но порядок должен быть во всём.",
        "В Школе 21 даже пробел должен знать своё место.",
        "Логика идеальная. Отступы решили стать главным героем.",
    ],
    "peer": [
        "Пришёл на пир проверить чужой код, а нашёл ошибку у себя.",
        "Объяснил решение другому студенту — внезапно сам всё понял.",
        "На пире мало сказать «работает». Нужно ещё объяснить почему.",
    ],
    "deadline": [
        "Дедлайн завтра. Проект официально переходит "
        "в режим ночной разработки.",
        "План: исправить баг за минуту. Реальность: уже два часа.",
        "Когда говоришь «осталось немного», но сам себе не веришь.",
    ],
    "bugs": [
        "Исправил один баг — появились два новых. "
        "Проект начал размножаться.",
        "«Я ничего не менял» — загадочная фраза разработчика.",
        "Код заработал. Почему — неизвестно. Сохрани копию!",
    ],
    "campus": [
        "Пришёл в кампус на пару часов. Вышел с десятью новыми вопросами.",
        "Время в кампусе измеряется количеством запусков компилятора.",
        "Тело уже дома, мысли всё ещё исправляют последний баг.",
    ],
    "git": [
        "git commit -m 'fix' — кратко, честно, без лишних подробностей.",
        "Перед git push всё спокойно. После git push начинается проверка нервов.",
        "Забыл сделать commit, зато отлично помнишь, что собирался.",
    ],
    "coffee": [
        "Кофе не исправляет код, но помогает смотреть на ошибку дольше.",
        "Сначала кофе, потом проект. Потом кофе, потому что проект не оценил первый.",
        "Заряд студента: 3%. Заряд ноутбука: 2%. Дедлайн: уже здесь.",
    ],
    "pool": [
        "🦫 Бобр слышит слово «бассейн» и чувствует себя экспертом по погружению.",
        "Бобр за здоровый баланс: иногда нужно выйти из кода и перевести дух.",
    ],
}

GENERAL_MEMES = [
    "🦫 В Школе 21 два состояния: «ничего не понимаю» "
    "и «не трогай, оно работает».",
    "Открыл документацию на минуту. Вернулся через час с десятью вкладками.",
    "План был идеальный. Потом запустили код.",
    "Ты не прокрастинируешь. Ты даёшь решению время созреть.",
    "Если проект работает — сохрани копию. Если идеально — сохрани три.",
    "Уровень уверенности растёт до момента запуска тестов.",
    "Самая оптимистичная фраза: «Сейчас быстро поправлю».",
]

HELP = (
    "🦫 БОБР 21 — твой напарник по Школе 21!\n\n"
    "📚 Полезные команды:\n"
    "• Мои задачи — показать список задач\n"
    "• Добавить задачу название — создать задачу\n"
    "• Готово 1 — отметить задачу № 1\n"
    "• Помощь — список команд\n"
    "• Мемы — случайная шутка\n\n"
    "💻 Темы для мемов:\n"
    "• Git и коммиты\n"
    "• Norminette\n"
    "• Вертер\n"
    "• Пиры\n"
    "• Баги и отладка\n"
    "• Кампус, бассейн и дедлайны\n\n"
    "Я помогу организовать задачи и пережить учёбу. 🦫"
)


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                task TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            )
        """)


def add_task(user_id, task):
    task = task.strip()

    if not task:
        return (
            "🦫 Напиши задачу после команды.\n"
            "Например: Добавить задачу разобраться с Git"
        )

    if len(task) > 300:
        return "🦫 Слишком длинная задача. Сократи её до 300 символов."

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO tasks (user_id, task) VALUES (?, ?)",
            (str(user_id), task),
        )

    return f"🦫 Записал в твой план:\n«{task}»\n\nНе забудь выполнить!"


def list_tasks(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT id, task, done
            FROM tasks
            WHERE user_id = ?
            ORDER BY done ASC, id ASC
            """,
            (str(user_id),),
        ).fetchall()

    if not rows:
        return (
            "🦫 Пока задач нет!\n\n"
            "Добавь первую:\n"
            "Добавить задачу разобраться с Git"
        )

    lines = ["🦫 ТВОИ ЗАДАЧИ\n"]

    for task_id, task, done in rows:
        status = "✅" if done else "⬜"
        lines.append(f"{status} {task_id}. {task}")

    completed = sum(row[2] for row in rows)
    total = len(rows)
    percent = int(completed / total * 100)

    lines.append(
        f"\n📊 Прогресс: {completed}/{total} ({percent}%)"
    )
    lines.append("\nЧтобы завершить задачу: Готово 1")

    return "\n".join(lines)


def complete_task(user_id, task_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            UPDATE tasks
            SET done = 1
            WHERE id = ? AND user_id = ? AND done = 0
            """,
            (task_id, str(user_id)),
        )

    if cursor.rowcount == 0:
        return (
            "🦫 Не нашёл незавершённую задачу с таким номером.\n"
            "Напиши «Мои задачи», чтобы проверить список."
        )

    return (
        "🦫 Отличная работа! Задача выполнена! 🎉\n"
        "Напиши «Мои задачи», чтобы посмотреть прогресс."
    )


def get_answer(text):
    lowered = text.lower().replace("ё", "е").strip()

    if lowered in (
        "/start", "привет", "начать", "здарова", "здравствуй"
    ):
        return (
            "🦫 Йоу! Я Бобр 21 — твой напарник по Школе 21!\n\n"
            "Помогу организовать задачи и разбавлю учёбу мемами.\n\n"
            "Напиши «Помощь», чтобы узнать команды."
        )

    if lowered in ("/help", "помощь", "команды"):
        return HELP

    if any(word in lowered for word in (
        "мем", "пошути", "рассмеши"
    )):
        return random.choice(GENERAL_MEMES)

    topics = [
        (("вертер", "проверка проекта"), "werter"),
        (("norminette", "норминет"), "norminette"),
        (("peer-to-peer", "peer", "пир", "пиры"), "peer"),
        (("дедлайн", "срок сдачи", "не успеваю"), "deadline"),
        (("баг", "ошибк", "сегфолт", "отлад"), "bugs"),
        (("кампус", "кластер"), "campus"),
        (("бассейн", "погружение"), "pool"),
        (("git", "коммит", "пуш", "push"), "git"),
        (("кофе", "энергетик", "не спал"), "coffee"),
    ]

    for keywords, topic in topics:
        if any(word in lowered for word in keywords):
            return random.choice(MEMES[topic])

    return (
        "🦫 Не совсем понял, но не переживай!\n\n"
        "Напиши «Помощь», чтобы увидеть команды, "
        "или задай вопрос про Git, вертер, Norminette и учёбу."
    )



def handle_message(user_id, text):
    lowered = text.lower().replace("ё", "е").strip()

    # Команды бота оставляем без изменений.
    if lowered in ("/start", "начать"):
        return get_answer("/start")

    if lowered in ("/help", "помощь", "команды"):
        return HELP

    if lowered in ("мои задачи", "список задач", "мои дела"):
        return list_tasks(user_id)

    prefix = "добавить задачу"

    if lowered == prefix or lowered.startswith(prefix + " "):
        task = text.strip()[len(prefix):].strip()
        return add_task(user_id, task)

    if lowered.startswith("готово "):
        number = lowered[len("готово "):].strip()

        if number.isdigit():
            return complete_task(user_id, int(number))

        return "🦫 Укажи номер задачи. Например: «Готово 1»."

    # Мемы по-прежнему выдаются по явной просьбе.
    if any(word in lowered for word in (
        "мем", "пошути", "рассмеши"
    )):
        return get_answer(text)

    # Приветствия и короткие обращения оставляем старой логике.
    if lowered in (
        "привет", "здарова", "здравствуй", "йоу",
        "git", "вертер", "norminette", "норминет",
        "peer", "пир", "кампус", "бассейн", "кофе"
    ):
        return get_answer(text)

    # Определяем, похож ли текст на вопрос к базе знаний.
    question_starts = (
        "что ", "как ", "зачем ", "почему ", "где ",
        "когда ", "сколько ", "какой ", "какая ",
        "какие ", "какое ", "можно ли ", "объясни ",
        "расскажи ", "помоги ", "чем ", "кто ",
        "каким образом "
    )

    is_question = (
        "?" in lowered
        or lowered.startswith(question_starts)
        or lowered.startswith((
            "git status", "git add", "git commit",
            "git push", "git log"
        ))
    )

    if is_question:
        try:
            return answer_question(text)
        except Exception as error:
            print("Ошибка RAG/Gemini:", error)
            return (
                "🦫 Не получилось обратиться к моей базе знаний.\n"
                "Попробуй немного позже. Твои задачи по-прежнему со мной!"
            )

    # Для остальных сообщений сохраняем старые реакции и мемы.
    return get_answer(text)



# ---------- МНОГОУРОВНЕВОЕ МЕНЮ MAX ----------

MENU_PAGES = {
    "main": [
        [("📚 Учёба", "menu:study"),
         ("📋 Мои задачи", "menu:tasks")],
        [("🤖 Спросить ИИ", "menu:ai"),
         ("😂 Мемы", "menu:memes")],
    ],
    "study": [
        [("🐙 Git", "menu:git"),
         ("🛡️ Вертер", "menu:verter")],
        [("📏 Norminette", "menu:norm"),
         ("🤝 Пиры", "menu:peer")],
        [("🏠 Главное меню", "menu:main")],
    ],
    "git": [
        [("🤖 Объяснить Git", "ask:git")],
        [("⬅️ Назад", "menu:study"),
         ("🏠 Главное меню", "menu:main")],
    ],
    "verter": [
        [("🤖 Спросить про Вертера", "ask:verter")],
        [("⬅️ Назад", "menu:study"),
         ("🏠 Главное меню", "menu:main")],
    ],
    "norm": [
        [("🤖 Спросить про Norminette", "ask:norm")],
        [("⬅️ Назад", "menu:study"),
         ("🏠 Главное меню", "menu:main")],
    ],
    "peer": [
        [("🤖 Спросить про пиры", "ask:peer")],
        [("⬅️ Назад", "menu:study"),
         ("🏠 Главное меню", "menu:main")],
    ],
    "tasks": [
        [("📝 Показать задачи", "task:list")],
        [("➕ Добавить задачу", "task:add")],
        [("⬅️ Назад", "menu:main"),
         ("🏠 Главное меню", "menu:main")],
    ],
    "ai": [
        [("🐙 Вопрос про Git", "ask:git")],
        [("📖 Задать свой вопрос", "ai:help")],
        [("⬅️ Назад", "menu:main"),
         ("🏠 Главное меню", "menu:main")],
    ],
    "memes": [
        [("🎲 Случайный мем", "meme:general")],
        [("🐛 Баги", "meme:bugs"),
         ("⏰ Дедлайны", "meme:deadline")],
        [("🐙 Git", "meme:git"),
         ("⬅️ Назад", "menu:main")],
        [("🏠 Главное меню", "menu:main")],
    ],
}

MENU_TEXTS = {
    "main": (
        "🦫 БОБР 21\n\n"
        "Добро пожаловать в нору!\n"
        "Выбирай, куда пойдём. "
        "Паниковать будем по расписанию."
    ),
    "study": "📚 УЧЁБА 21\n\nВыбери тему:",
    "git": "🐙 GIT И GITHUB\n\nЧто разберём? Бобёр готов к коммиту.",
    "verter": "🛡️ ВЕРТЕР\n\nРазберёмся с проверкой проекта.",
    "norm": "📏 NORMINETTE\n\nДаже пробелы здесь живут по правилам.",
    "peer": "🤝 PEER-TO-PEER\n\nВремя проверить код и объяснить, почему он работает.",
    "tasks": "📋 ТВОИ ЗАДАЧИ\n\nВыбирай действие:",
    "ai": "🤖 СПРОСИТЬ ИИ\n\nВыбери тему или напиши вопрос обычным сообщением.",
    "memes": "😂 МЕМЫ\n\nВыбирай вид студенческой боли:",
}


def make_keyboard(rows):
    """Создаёт inline-клавиатуру MAX."""
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "callback",
                        "text": title,
                        "payload": action,
                    }
                    for title, action in row
                ]
                for row in rows
            ]
        },
    }


def menu_keyboard(page):
    rows = MENU_PAGES.get(page, MENU_PAGES["main"])
    return make_keyboard(rows)


def home_keyboard():
    return make_keyboard([
        [("🏠 Открыть меню", "menu:main")]
    ])


def send_callback_answer(callback_id, text, keyboard=None):
    """Обновляет сообщение, на кнопке которого нажали."""
    message = {"text": text}

    if keyboard:
        message["attachments"] = [keyboard]

    response = requests.post(
        f"{API}/answers",
        params={"callback_id": callback_id},
        headers=HEADERS,
        json={"message": message},
        timeout=20,
        verify=CA_BUNDLE,
    )
    response.raise_for_status()


def handle_callback(user_id, callback_id, payload):
    """Обрабатывает нажатия на кнопки меню."""
    try:
        if payload.startswith("menu:"):
            page = payload.split(":", 1)[1]

            if page not in MENU_TEXTS:
                page = "main"

            text = MENU_TEXTS[page]

            # В разделе задач сразу показываем список.
            if page == "tasks":
                text += "\n\n" + list_tasks(user_id)

            send_callback_answer(
                callback_id,
                text,
                menu_keyboard(page),
            )
            return

        if payload == "task:list":
            send_callback_answer(
                callback_id,
                list_tasks(user_id),
                menu_keyboard("tasks"),
            )
            return

        if payload == "task:add":
            send_callback_answer(
                callback_id,
                "🦫 Напиши следующим сообщением:\n\n"
                "Добавить задачу разобраться с Git\n\n"
                "Я сохраню её в твой список.",
                menu_keyboard("tasks"),
            )
            return

        if payload == "ai:help":
            send_callback_answer(
                callback_id,
                "🤖 Напиши вопрос обычным сообщением.\n\n"
                "Например: «Объясни git commit на примере».\n"
                "Бобр попробует найти информацию в документах "
                "и подготовить ответ с помощью Gemini.",
                menu_keyboard("ai"),
            )
            return

        if payload.startswith("ask:"):
            topic = payload.split(":", 1)[1]

            questions = {
                "git": "Объясни Git и основные команды Git новичку.",
                "verter": "Объясни, что такое Вертер в учебном процессе Школы 21.",
                "norm": "Объясни, что такое Norminette и для чего она нужна.",
                "peer": "Объясни, что такое peer-to-peer проверка в обучении.",
            }

            question = questions.get(topic)

            if not question:
                send_callback_answer(
                    callback_id,
                    "🦫 Не нашёл такую тему.",
                    menu_keyboard("study"),
                )
                return

            try:
                answer = answer_question(question)
            except Exception as error:
                print("Ошибка RAG/Gemini:", error)
                answer = (
                    "🦫 Не удалось получить ответ от ИИ. "
                    "Попробуй немного позже."
                )

            send_callback_answer(
                callback_id,
                answer or "🦫 Бобр задумался. Попробуй ещё раз.",
                menu_keyboard(topic if topic in MENU_PAGES else "study"),
            )
            return

        if payload.startswith("meme:"):
            topic = payload.split(":", 1)[1]

            if topic == "general":
                joke = random.choice(GENERAL_MEMES)
            else:
                joke = random.choice(
                    MEMES.get(topic, GENERAL_MEMES)
                )

            send_callback_answer(
                callback_id,
                joke,
                menu_keyboard("memes"),
            )
            return

        send_callback_answer(
            callback_id,
            "🦫 Не понял эту кнопку. Вернёмся в главное меню?",
            menu_keyboard("main"),
        )

    except requests.RequestException as error:
        print("Ошибка обработки кнопки MAX:", error)

def check_bot():
    response = requests.get(
        f"{API}/me",
        headers=HEADERS,
        timeout=20,
        verify=CA_BUNDLE,
    )
    response.raise_for_status()

    print("MAX подключён! Информация о боте:")
    print(response.json())



def send_reply(user_id, text, keyboard=None):
    body = {"text": text}

    if keyboard:
        body["attachments"] = [keyboard]

    response = requests.post(
        f"{API}/messages",
        params={"user_id": user_id},
        headers=HEADERS,
        json=body,
        timeout=20,
        verify=CA_BUNDLE,
    )
    response.raise_for_status()
    print("Ответ отправлен!")


def main():
    check_bot()
    init_db()

    print("🦫 Бобр 21 запущен!")
    print("Нажми Ctrl+C для остановки.")

    marker = None

    while True:
        try:
            params = {"timeout": 30}

            if marker is not None:
                params["marker"] = marker

            response = requests.get(
                f"{API}/updates",
                headers=HEADERS,
                params=params,
                timeout=40,
                verify=CA_BUNDLE,
            )
            response.raise_for_status()

            data = response.json()
            marker = data.get("marker", marker)

            for update in data.get("updates", []):
                if update.get("update_type") == "message_callback":
                    callback = update.get("callback") or {}
                    callback_id = callback.get("callback_id")
                    payload = callback.get("payload") or ""

                    user = (
                        callback.get("user")
                        or update.get("user")
                        or {}
                    )
                    user_id = user.get("user_id")

                    if user_id is None:
                        callback_message = update.get("message") or {}
                        callback_sender = callback_message.get("sender") or {}
                        user_id = callback_sender.get("user_id")

                    if callback_id and payload and user_id is not None:
                        print(f"Нажата кнопка: {payload}")
                        handle_callback(user_id, callback_id, payload)

                    continue

                if update.get("update_type") != "message_created":
                    continue

                message = update.get("message") or {}
                sender = message.get("sender") or {}
                body = message.get("body") or {}

                user_id = sender.get("user_id")
                message_text = (body.get("text") or "").strip()

                if user_id is None or not message_text:
                    continue

                print(f"Получено сообщение: {message_text}")

                try:
                    normalized = message_text.lower().replace("ё", "е").strip()

                    if normalized in ("/start", "начать", "меню", "/menu"):
                        send_reply(
                            user_id,
                            MENU_TEXTS["main"],
                            menu_keyboard("main"),
                        )
                        continue

                    answer = handle_message(user_id, message_text)
                    send_reply(user_id, answer, home_keyboard())
                except requests.RequestException as error:
                    print("Не удалось отправить ответ:", error)

                except requests.RequestException as error:
                    print("Не удалось отправить ответ:", error)

        except KeyboardInterrupt:
            print("\n🦫 Бобр пошёл отдыхать. Пока!")
            break

        except requests.RequestException as error:
            print("Ошибка запроса к MAX:", error)
            time.sleep(3)


if __name__ == "__main__":
    main()
