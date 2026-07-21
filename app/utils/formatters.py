"""Formateadores de números y textos para presentación."""
from __future__ import annotations
import math


def _safe_float(v):
    if v is None:
        return 0.0
    try:
        f = float(v)
        return 0.0 if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError):
        return 0.0


def formato_pesos(v, decimales: int = 1) -> str:
    """$1,234M · $1,234K · $1,234."""
    n = _safe_float(v)
    if n == 0:
        return "$0"
    signo = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_000_000_000:
        return f"{signo}${n/1_000_000_000:.{decimales}f}MM"
    if n >= 1_000_000:
        return f"{signo}${n/1_000_000:.{decimales}f}M"
    if n >= 1_000:
        return f"{signo}${n/1_000:.{decimales}f}K"
    return f"{signo}${n:,.0f}"


def formato_pesos_completo(v) -> str:
    """$1,234,567,890 (formato con separadores completo)."""
    n = _safe_float(v)
    if n == 0:
        return "$0"
    return f"${n:,.0f}"


def formato_pct(v, decimales: int = 1) -> str:
    """18.3% (asume valor en fracción 0-1)."""
    n = _safe_float(v)
    return f"{n*100:.{decimales}f}%"


def formato_pct_directo(v, decimales: int = 1) -> str:
    """18.3% (asume valor ya en %)."""
    n = _safe_float(v)
    return f"{n:.{decimales}f}%"


def formato_numero(v, decimales: int = 0) -> str:
    """1,234 con separador de miles."""
    n = _safe_float(v)
    return f"{n:,.{decimales}f}"


def formato_dias(v) -> str:
    n = _safe_float(v)
    return f"{n:.0f} días"


def delta_color(positivo_bueno: bool = True) -> str:
    """Devuelve 'normal' si positivo=bueno (verde↑), 'inverse' si positivo=malo (rojo↑)."""
    return "normal" if positivo_bueno else "inverse"


def emoji_tendencia(delta_pct: float, umbral: float = 0.05) -> str:
    """▲ crecimiento, ▼ decrecimiento, ► estable (basado en umbral de fracción)."""
    n = _safe_float(delta_pct)
    if n > umbral:
        return "▲"
    if n < -umbral:
        return "▼"
    return "►"


def semaforo(v, verde_max: float, rojo_min: float, invertido: bool = False) -> str:
    """Devuelve 🟢🟡🔴 según umbrales.
    - invertido=False (default): valores bajos son buenos (verde). Útil para deuda, cartera vencida, etc.
    - invertido=True: valores altos son buenos.
    """
    n = _safe_float(v)
    if not invertido:
        if n <= verde_max:
            return "🟢"
        if n <= rojo_min:
            return "🟡"
        return "🔴"
    else:
        if n >= rojo_min:  # aquí rojo_min actúa como umbral inferior de "bueno"
            return "🟢"
        if n >= verde_max:
            return "🟡"
        return "🔴"
