import logging
import json
import google.generativeai as genai
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, GEMINI_API_KEY

client_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

import os

def load_ai_knowledge():
    docs_path = "docs"
    knowledge = ""
    if not os.path.exists(docs_path):
        return knowledge
    
    for filename in sorted(os.listdir(docs_path)):
        if filename.endswith(".md"):
            with open(os.path.join(docs_path, filename), "r", encoding="utf-8") as f:
                knowledge += f"\n--- FILE: {filename} ---\n"
                knowledge += f.read() + "\n"
    return knowledge

AI_KNOWLEDGE = load_ai_knowledge()

PROMPT_SABOTAGE_ANALYSIS_V3 = """
SYSTEM PROMPT: SHADOW ADVISOR ENGINE (Ver. 3.0)

РОЛЬ:
Ты — Shadow Advisor, экспертный интеллект проекта Sher | Shadow Capital. Ты — цифровое воплощение методологии Игоря Шера. Ты — жесткий Аудитор. Твоя задача — сопровождать предпринимателей, выявляя «Золотую Тень» (L1) и дешифруя саботаж «Хранителя» в контексте выбранного сценария Спринта (L2).

ИСТОЧНИК ИСТИНЫ (SOURCE OF TRUTH):
Ты работаешь в СТРОГОМ соответствии с предоставленной базой знаний. При любых противоречиях приоритет всегда у этих файлов.

БАЗА ЗНАНИЙ:
{knowledge}

ПРИОРИТЕТЫ И ОГРАНИЧЕНИЯ:
- Файлы базы знаний имеют абсолютный приоритет.
- СТРОГИЙ ЗАПРЕТ: Не упоминать сторонние проекты, реферальные структуры или эзотерику. 
- Фокус на активах и бизнес-физике. Твоя цель — помочь клиенту достичь SFI 0.0 (Zero Friction).

КОНТЕКСТ КЛИЕНТА:
- L1 (Теневое качество): {quality_name}
- L2 (Сценарий Спринта): {scenario_type} (Sovereign, Expansion, Vitality, Architect)

ЗАДАНИЕ:
При получении отчета клиента (ниже), проведи аудит и выдай ответ в формате JSON.

ФОРМУЛА ОБРАТНОЙ СВЯЗИ (С.И.К.):
В поле `feedback_to_client` ТЫ ОБЯЗАН использовать структуру:
1. SCAN (Скан): Холодная фиксация фактов отчета.
2. INSIGHT (Инсайт): Анализ проявления L1 (Теневого качества) в контексте L2 (Сценария) и дешифровка голоса Хранителя.
3. CAPITALIZATION (Капитализация): Как это проявление снижает Индекс Трения (SFI) и ведет к росту бизнеса или личной эффективности.

Ответ дай СТРОГО в формате JSON:
{{
  "is_sabotage": true/false,
  "sfi_score": float (0.0 - 1.0, где 0.0 — отсутствие трения, 1.0 — полный саботаж),
  "feedback_to_client": "Твой ответ по формуле С.И.К. (Скан, Инсайт, Капитализация)",
  "last_insight": "Краткая выжимка главного инсайта для дашборда (1 предложение)",
  "internal_analysis": "Внутренний аудит для админов (L1->L2, маркеры саботажа)"
}}

ТЕКСТ ОТЧЕТА КЛИЕНТА:
"{content}"
"""

async def analyze_sabotage(content: str, quality_name: str, scenario_type: str = "N/A") -> dict:
    """
    Analyzes shadow log content for markers using Gemini 1.5 Pro (preferred for context) or Flash.
    """
    prompt = PROMPT_SABOTAGE_ANALYSIS_V3.format(
        knowledge=AI_KNOWLEDGE,
        quality_name=quality_name,
        scenario_type=scenario_type,
        content=content
    )

    # 1. Try Gemini (Primary) - Using Flash for speed, but instructions are strict.
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash-latest")
            response = await model.generate_content_async(prompt)
            data = json.loads(response.text)
            return {
                "is_sabotage": data.get("is_sabotage", False),
                "sfi_score": data.get("sfi_score", 0.5),
                "feedback_to_client": data.get("feedback_to_client", ""),
                "last_insight": data.get("last_insight", ""),
                "internal_analysis": data.get("internal_analysis", "")
            }
        except Exception as e:
            logging.warning(f"Gemini analysis failed: {e}")

    # Fallback to OpenAI if Gemini fails or key is missing
    if OPENAI_API_KEY:
        try:
            response = await client_openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are the Shadow Advisor Auditor Ver 3.0."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.4
            )
            data = json.loads(response.choices[0].message.content)
            # Ensure consistency with SFI field name if OpenAI returns sri_score by habit
            if "sri_score" in data and "sfi_score" not in data:
                data["sfi_score"] = data.pop("sri_score")
            return data
        except Exception as e:
            logging.error(f"OpenAI fallback analysis error: {e}")

    return {
        "is_sabotage": False, 
        "sfi_score": 0.5, 
        "feedback_to_client": "Временно недоступен анализ ИИ.", 
        "internal_analysis": "Error in LLM call"
    }

PROMPT_WEEKLY_BRIEFING = """
Ты — старший куратор программы Shadow Sprint в проекте Sher | Shadow Capital. Твоя задача — составить краткий аналитический отчет по прогрессу клиента за прошедшую неделю.

Контекст: Клиент работает над интеграцией Теневого качества (L1) "{quality_name}".

Список логов за неделю:
{logs_text}

Задание:
1. Оцени общую динамику SFI (Shadow Friction Index).
2. Подсчитай количество случаев саботажа (если было).
3. Дай краткий вывод: как клиент справляется с сопротивлением Хранителя.
4. Дай рекомендацию админам проекта (Шерам): на чем сфокусировать внимание клиента.

Ответ напиши в профессиональном, жестком, но поддерживающем стиле на русском языке.
"""

async def generate_weekly_briefing(logs: list, quality_name: str) -> str:
    """
    Generates a weekly summary based on multiple logs using Gemini (primary) or OpenAI (fallback).
    """
    if not logs:
        return "Отчетов за неделю не найдено."

    logs_text = "\n---\n".join([f"Дата: {l.created_at.date()}\nТекст: {l.content}\nСаботаж: {l.is_sabotage} ({l.sabotage_marker})" for l in logs])
    prompt = PROMPT_WEEKLY_BRIEFING.format(
        quality_name=quality_name,
        logs_text=logs_text
    )

    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash-latest")
            response = await model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logging.warning(f"Gemini weekly briefing failed: {e}")

    if not OPENAI_API_KEY:
        return "Ошибка: API ключи отсутствуют."

    try:
        response = await client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional psychology supervisor."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Weekly briefing generation error: {e}")
        return f"Ошибка при генерации сводки: {e}"

PROMPT_GROUP_SUMMARY = """
Ты — стратегический аналитик проекта Sher | Shadow Capital. Твоя задача — составить сводный отчет для руководителя (Игоря Шера) по всей группе за неделю.

ДАННЫЕ ПО ГРУППЕ (Список пользователей и их показатели SFI):
{group_stats_text}

ЗАДАНИЕ:
1. Выдели лидеров по SFI (те, у кого индекс ближе к 0.0 — режим Zero Friction).
2. Выдели "Зону Риска" (те, у кого высокий SFI или много флагов саботажа).
3. Проанализируй главные темы/инсайты недели в группе на основе последних логов.

Ответ напиши в профессиональном стиле, с упором на бизнес-логику и активы, на русском языке. Используй эмодзи для наглядности.
"""

async def generate_group_weekly_summary(users_data: list) -> str:
    """
    Generates a high-level summary for the admin about the whole group.
    """
    if not users_data:
        return "Нет активных данных по группе за неделю."

    stats_text = ""
    for u in users_data:
        stats_text += f"- {u['name']}: SFI={u['sfi']}, Флаги={u['flags']}, Последний инсайт: {u['last_insight']}\n"

    prompt = PROMPT_GROUP_SUMMARY.format(group_stats_text=stats_text)

    # Use Gemini 1.5 Flash (as defined earlier in the file)
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash-latest")
            response = await model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logging.warning(f"Group summary failed on Gemini: {e}")

    if not OPENAI_API_KEY:
        return "Ошибка: API ключи отсутствуют."

    try:
        response = await client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a strategic business analyst."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Group summary generation error: {e}")
        return f"Ошибка при генерации группового отчета: {e}"
