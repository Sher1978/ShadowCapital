from aiogram.utils.markdown import hbold, hitalic

# --- Video Placeholder IDs ---
# Replace these with real Telegram file_ids once uploaded
VIDEO_VERDICT = {
    "A": "BAACAgIAAxkBAAIHGmnWl5TVI748eYE_UvU-8B6LUx0tAAIumwAC3l6xSre88v3_C4JqOwQ",
    "B": "BAACAgIAAxkBAAIHHmnWl_CAlVErCdb0rbUe9qze1v1VAAIvmwAC3l6xSqVcSWtC2cwaOwQ",
    "C": "BAACAgIAAxkBAAIHImnWmC2Dng6kZ7dg4jNok0NTjD-8AAIxmwAC3l6xShcgTnjEDYO4OwQ",
    "D": "BAACAgIAAxkBAAIHJmnWmFN57mJ1uxj-AloXPdaPl8BdAAIzmwAC3l6xSlruFHMjJAwtOwQ"
}

VIDEO_CURRENCY = {
    "money": "BAACAgIAAxkBAAIHKmnWmIYONxqBO46BgEr8zzDYZ2oKAAI2mwAC3l6xSn_3dT1MQNs_OwQ",
    "time": "BAACAgIAAxkBAAIHLmnWmKuk9mTexx7kKjzrHZnajfsYAAI4mwAC3l6xSgS-AvBHlHaNOwQ",
    "status": "BAACAgIAAxkBAAIHMmnWmNhdqRCiwaWJmCAq0XZru_pHAAI6mwAC3l6xSsscdmXsIQy5OwQ",
    "libido": "BAACAgIAAxkBAAIHNmnWmQ3c2OZRMIsN7-klgK3kJ4zmAAI9mwAC3l6xSkqjCINRMoXyOwQ"
}

# --- Verdict Texts ---
VERDICT_TEXTS = {
    "A": (
        f"{hbold('Сценарий A (Sovereign):')}\n"
        f"• {hbold('Что заблокировано:')} Твое право на автономию и жесткое «Нет». Внутри тебя сидит Хозяин, но он заперт в подвале из страха обидеть окружающих.\n"
        f"• {hbold('Цена, которую ты платишь:')} Ты — бесплатный донор. Ты тратишь 80% жизни на решение чужих проблем и «спасение» тех, кто на тебе едет. Тебя считают «удобным», но с тобой не считаются."
    ),
    "B": (
        f"{hbold('Сценарий B (Expansion):')}\n"
        f"• {hbold('Что заблокировано:')} Твой истинный масштаб и право на избыток. Заблокирована наглость, позволяющая занимать всё пространство. Ты приучил себя «не высовываться».\n"
        f"• {hbold('Цена, которую ты платишь:')} Ты — лучший в тени худших. Пока ты воспитанно ждешь очереди, наглые выскочки забирают твои деньги и твое внимание. Ты в 10 раз меньше, чем должен быть."
    ),
    "C": (
        f"{hbold('Сценарий C (Vitality):')}\n"
        f"• {hbold('Что заблокировано:')} Твои животные инстинкты и дикая энергия. Ты заблокировал Либидо, заменив его маской «продуктивного робота». Тело больше не генерирует огонь.\n"
        f"• {hbold('Цена, которую ты платишь:')} Ты — биоробот со сгоревшим предохранителем. Жизнь стала черно-белым кино. Твои цели тебя не греют, ты на грани выгорания, за которым — пустота."
    ),
    "D": (
        f"{hbold('Сценарий D (Architect):')}\n"
        f"• {hbold('Что заблокировано:')} Твоя связь с иррациональным и право на риск. Ты запер «Творца Хаоса» в клетку логических схем. Ты до смерти боишься неопределенности.\n"
        f"• {hbold('Цена, которую ты платишь:')} Ты строишь карточные домики из логики, которые рушатся от любого дуновения реальности. Ты упускаешь квантовые скачки, живя в предсказуемом тупике."
    )
}

ROI_DATA = {
    "A": {
        "money": "Возврат «слитых» ресурсов.",
        "time": "+15 часов свободы в неделю.",
        "status": "Тишина и подчинение.",
        "libido": "Ведущая роль в жизни."
    },
    "B": {
        "money": "Рост чека в 2–3 раза.",
        "time": "0 минут ожидания разрешений.",
        "status": "Имя-бренд, центр внимания.",
        "libido": "Магнетизм масштаба."
    },
    "C": {
        "money": "Прибыль через скорость.",
        "time": "4 часа работы вместо 40.",
        "status": "Животный авторитет.",
        "libido": "Пик витальной энергии."
    },
    "D": {
        "money": "Квантовый скачок в хаосе.",
        "time": "Экономия годов жизни.",
        "status": "Репутация провидца.",
        "libido": "Творческий экстаз."
    }
}

def get_roi_report(scenario: str) -> str:
    """Generates a personalized ROI report based on the scenario."""
    data = ROI_DATA.get(scenario, ROI_DATA["A"])
    return (
        f"📊 {hbold('Теневой Профит: Твои показатели через 30 дней')}\n\n"
        f"💰 {hbold('ДЕНЬГИ')}: {data['money']}\n"
        f"⏳ {hbold('ВРЕМЯ')}: {data['time']}\n"
        f"👑 {hbold('СТАТУС')}: {data['status']}\n"
        f"🔥 {hbold('ЛИБИДО')}: {data['libido']}"
    )

# --- Currency Choice Blow ---
CURRENCY_BLOW = {
    "money": "«Твоя скромность — это налог на бедность. Пора его отменить».",
    "time": "«Ты не занят, ты — донор. Забери свою жизнь себе».",
    "status": "«Авторитет — это запах твоей силы. Пусть они начнут тебя слышать».",
    "libido": "«Либидо — это твой ядерный реактор. Без него всё остальное мертво»."
}

# --- Final Offer Text ---
FINAL_OFFER_TEXT = (
    "Ты можешь продолжать жать педаль газа на ручнике, удивляясь, почему нет скорости. "
    "Но если ты готов решить вопрос раз и навсегда и вернуться в состояние \"хочу и могу\" — нам нужно поговорить лично.\n\n"
    "Я не беру в систему всех. Мне нужно убедиться, что ты готов к той скорости, которую дает Human OS.\n\n"
    f"{hbold('Записывайся на Аудит Тени.')} 15 минут, которые изменят твой код навсегда."
)
