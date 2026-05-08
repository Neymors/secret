"""
Amygdalé — Utility: Formatting
Maneja la presentación visual de números, monedas y fechas.
"""

def format_usd(value: float) -> str:
    """Formatea un número como USD ($1,234.56)."""
    if value is None:
        return "$0.00"
    return f"${abs(value):,.2f}"

def format_ars(value: float) -> str:
    """Formatea un número como ARS ($1.234,56)."""
    if value is None:
        return "$0,00"
    # Locale es-AR usa punto para miles y coma para decimales
    return f"${abs(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def format_pct(value: float) -> str:
    """Formatea un porcentaje con signo (+12.34% o -5.00%)."""
    if value is None:
        return "0.00%"
    sign = "+" if value >= 0 else "−" # Usamos el guion largo para estética
    return f"{sign}{abs(value):.2f}%"

def format_qty(value: float) -> str:
    """Formatea cantidades con 2 decimales fijos."""
    if value is None:
        return "0.00"
    return f"{value:.2f}"

def format_weight(value: float) -> str:
    """Formatea pesos de cartera (%) con 1 decimal."""
    if value is None:
        return "0.0%"
    return f"{value:.1f}%"

def format_date(date_str: str) -> str:
    """Convierte ISO date string a formato corto DD/MM."""
    if not date_str:
        return ""
    try:
        # Asumiendo formato YYYY-MM-DD
        parts = date_str.split('-')
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}" # DD/MM
    except Exception:
        pass
    return date_str