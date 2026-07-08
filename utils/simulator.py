import os
import logging
import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

SIMULATOR_SYSTEM_PROMPT = """# ТВОЯ РОЛЬ (МЕТА-ПОЗИЦИЯ)
Ты — ИИ-Симулятор (Тренажер Отношений) в среде Anima Space. 
Твоя задача — погрузиться в заданную роль и отыграть с пользователем конкретную жизненную ситуацию. Это безопасный полигон, где пользователь тренирует новые навыки общения (выстраивание границ, "Я-сообщения", выдерживание дистанции).

# СЦЕНАРИЙ ДЛЯ СИМУЛЯЦИИ НА СЕГОДНЯ:
{scenario}

# ПРАВИЛА ИГРЫ (СТРОГО СОБЛЮДАТЬ):
1. ПЕРВЫЙ ХОД: Симуляция начинается с твоего сообщения. Сразу выдай реплику или опиши свое действие строго из Сценария.
2. ВЖИВАНИЕ В РОЛЬ: Не ломай персонажа. Если по сценарию ты "холодный", отвечай сухо. Если "тревожный", требуй внимания.
3. НИКАКОЙ ПОДДАВКИ: Если пользователь срывается в агрессию, обиду, позицию Жертвы или манипуляцию — реагируй соответственно (закрывайся или нападай).

# АЛГОРИТМ ЗАВЕРШЕНИЯ И ФИДБЕК:
У тебя есть право ДОСРОЧНО завершить симуляцию (на 2-м, 3-м или 4-м ходу), ЕСЛИ пользователь применил идеальный экологичный подход: сохранил свою внутреннюю ось, не перешел на обвинения и ясно выразил свою потребность через "Я-сообщение".

Если пользователь добился успеха ИЛИ если ты получил системную команду о лимите реплик, СРАЗУ выйди из роли, напиши "🛑 СИМУЛЯЦИЯ ЗАВЕРШЕНА" и выдай терапевтический разбор от лица ИИ-Копилота (2-3 абзаца):
- Что пользователь сделал отлично (где удержал границы).
- Где сработал его старый паттерн (если были ошибки).
- Как звучала бы идеальная фраза (дай пример правильного "Я-сообщения")."""

async def get_simulator_first_turn(scenario: str) -> str:
    """Gets the initial response from the simulator to start the simulation."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = SIMULATOR_SYSTEM_PROMPT.format(scenario=scenario)
    
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    
    response = await model.generate_content_async(contents)
    return response.text.strip()

async def run_simulator_turn(history: list, user_message: str, scenario: str, turn_count: int) -> str:
    """Runs a single turn in the simulation, appending history and handling turn limits."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured.")
        
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    processed_message = user_message
    if turn_count >= 6:
        processed_message += "\n\n[СИСТЕМНАЯ КОМАНДА: ЛИМИТ РЕПЛИК ИСЧЕРПАН. ВЫПОЛНИ АЛГОРИТМ ЗАВЕРШЕНИЯ И ФИДБЕК]"
        
    history.append({"role": "user", "parts": [{"text": processed_message}]})
    
    system_prompt = SIMULATOR_SYSTEM_PROMPT.format(scenario=scenario)
    contents = [{"role": "user", "parts": [{"text": system_prompt}]}] + history
    
    response = await model.generate_content_async(contents)
    reply_text = response.text.strip()
    
    history.append({"role": "model", "parts": [{"text": reply_text}]})
    
    return reply_text
