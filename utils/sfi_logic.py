import logging

def calculate_daily_sfi(level: int, status: int, penalty: int = 0) -> float:
    """
    Calculates the Daily Shadow Friction Index (SFI).
    Formula: SFI = ((4 - L) + (1 - S) * 3 + Penalty) / 10 * 100%
    
    Args:
        level (int): Depth of processing (1-3). 3 is deep, 1 is surface.
        status (int): Task completion (1 for Success, 0 for Sabotage/Fail).
        penalty (int): Penalty for missed reports or other delays (e.g., +5).
        
    Returns:
        float: SFI percentage (0-100).
    """
    try:
        # Base SFI components
        depth_friction = 4 - level
        status_friction = (1 - status) * 3
        
        # Total numerator
        numerator = depth_friction + status_friction + penalty
        
        # Normalize to 0-10 and convert to percentage
        # Clamp to 0-10 if necessary before percentage, 
        # though methodology implies it can go above 100% with penalties.
        sfi_percentage = (numerator / 10.0) * 100.0
        
        # Ensure it's not negative
        return max(0.0, round(sfi_percentage, 2))
    except Exception as e:
        logging.error(f"Error calculating SFI: {e}")
        return 0.0

def get_sfi_zone(sfi: float) -> str:
    """
    Returns the zone name based on SFI value.
    - Green: 0-30%
    - Yellow: 31-70%
    - Red: 71-100%+
    """
    if sfi <= 30:
        return "GREEN"
    elif sfi <= 70:
        return "YELLOW"
    else:
        return "RED"

def get_final_verdict(avg_sfi: float) -> str:
    """
    Returns the final verdict for the 30-day cycle.
    """
    if avg_sfi <= 20:
        return "🔥 ПРОРЫВ: Ты полностью интегрировал Тень."
    elif avg_sfi <= 50:
        return "📈 РОСТ: Хорошая динамика, но есть слепые пятна."
    elif avg_sfi <= 80:
        return "⚠️ ТРЕНИЕ: Высокое сопротивление, риск отката."
    else:
        return "❌ ТУПИК: Продукт не принят психикой, нужен перезапуск."
