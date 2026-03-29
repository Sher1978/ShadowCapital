import os
import requests
import logging

logger = logging.getLogger(__name__)

def send_sfi_email(to_email, name, sfi_score, archetype, diagnostic_text):
    """
    Sends an SFI report via Resend API.
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.warning("📩 [EMAIL] Sending skipped: RESEND_API_KEY not set.")
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Format the HTML content
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; background-color: #0f172a; color: #f8fafc; border-radius: 12px; border: 1px solid #1e293b;">
        <h1 style="color: #38bdf8; text-align: center;">🗝 Shadow SFI: Ваш Досье</h1>
        <p>Привет, {name}!</p>
        <p>Ваш результат сканирования в системе SFI готов. Ниже представлены ключевые показатели Вашего Теневого Капитала.</p>
        
        <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0; font-size: 1.2em;">📊 <b>Итоговый SFI Index:</b> {sfi_score}%</p>
            <p style="margin: 0; font-size: 1.2em;">🏆 <b>Ведущий Архетип:</b> {archetype}</p>
        </div>

        <h3 style="color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 5px;">🧬 ПОЛНАЯ ДИАГНОСТИКА:</h3>
        <div style="white-space: pre-wrap; line-height: 1.6; color: #cbd5e1;">
            {diagnostic_text.replace('\n', '<br>')}
        </div>

        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #334155; text-align: center; color: #94a3b8; font-size: 0.9em;">
            <p>Это первый шаг к конвертации Теневого Капитала в реальный результат.</p>
            <p>Ожидайте сообщения от Игоря, мы уже анализируем Вашу стратегию.</p>
        </div>
    </div>
    """

    payload = {
        "from": "Shadow Sprint <onboarding@resend.dev>", # Update this once domain is verified
        "to": [to_email],
        "subject": f"🎯 Ваш SFI Отчет: {sfi_score}% — {archetype}",
        "html": html_content
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"✅ [EMAIL] Report sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ [EMAIL] Error sending to {to_email}: {e}")
        return False
