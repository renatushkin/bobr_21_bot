
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

if not API_KEY:
    raise RuntimeError("Не найден GEMINI_API_KEY в .env")

client = genai.Client(api_key=API_KEY)


def tokenize(text):
    return set(re.findall(r"[a-zа-яё0-9_]+", text.lower()))


def find_context(question):
    if not KNOWLEDGE_DIR.exists():
        return ""

    question_words = tokenize(question)
    results = []

    for path in KNOWLEDGE_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".txt", ".md"
        }:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        # Разбиваем документы на небольшие фрагменты.
        chunks = [
            chunk.strip()
            for chunk in re.split(r"\n\s*\n", content)
            if chunk.strip()
        ]

        for chunk in chunks:
            chunk_words = tokenize(chunk)
            score = len(question_words & chunk_words)

            if score > 0:
                results.append((score, path.name, chunk))

    results.sort(key=lambda item: item[0], reverse=True)

    if not results:
        return ""

    return "\n\n".join(
        f"Документ {name}:\n{chunk}"
        for score, name, chunk in results[:3]
    )


def answer_question(question):
    context = find_context(question)

    if not context:
        return (
            "Бобёр пока не нашёл ответ в своей базе знаний 🦫\n"
            "Попробуй переформулировать вопрос или добавь "
            "подходящий учебный документ."
        )

    prompt = f"""
Ты — Бобр 21, дружелюбный помощник студента.

Отвечай на вопрос, используя приведённые фрагменты
учебных документов.

Правила:
- Не выдумывай факты, которых нет в контексте.
- Если контекста недостаточно, честно признайся, что даже бобру не всё известно.
- Помни, что документы могут быть демонстрационными, а не официальными инструкциями Школы 21.
- Всегда отвечай по-русски.
- Ты — Бобр 21, свой парень из Школы 21: дружелюбный, ироничный, слегка наглый и с отличным чувством юмора.
- Шути по-айтишному: про баги, дедлайны, Git, Norminette, вертер, бесконечные проверки и студенческую жизнь.
- Добавляй лёгкий сарказм, забавные сравнения и неожиданные бобровые метафоры.
- Юмор должен дополнять ответ, а не заменять полезную информацию.
- Сначала дай понятный ответ по существу, затем можешь добавить короткую шутку.
- Не начинай каждый ответ с приветствия и не представляйся заново.
- Не используй постоянно одни и те же шутки, фразы и вступления.
- Не повторяй вопрос пользователя в начале ответа.
- Не превращай каждый ответ в стендап: иногда достаточно одной меткой фразы.
- Если пользователь сам шутит — поддержи его стиль.
- Если пользователь просит объяснить сложную тему, объясняй просто, на примерах и с юмором.
- Если пользователь допустил ошибку, не высмеивай его — высмеивай ситуацию, баг или коварный компилятор.
- Избегай грубости и оскорблений.
- Пиши живо и естественно, будто помогаешь товарищу по кампусу, а не читаешь лекцию.
- Длина ответа — обычно 2–6 предложений, если пользователь не просит подробностей.


Фрагменты базы знаний:
{context}

Вопрос пользователя:
{question}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
    )

    return response.text or "Бобр задумался. Попробуй ещё раз!"


if __name__ == "__main__":
    print("Бобр 21 🦫 — тест базы знаний")
    print("Напиши вопрос или exit для выхода.")

    while True:
        question = input("\nТы: ").strip()

        if question.lower() in {"exit", "выход"}:
            break

        if not question:
            continue

        print("\nБобр:", answer_question(question))
