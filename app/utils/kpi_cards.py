"""Componente KPI: tarjetas con valor + delta + semáforo opcional."""
from __future__ import annotations
from typing import Any

import streamlit as st


def kpi_row(kpis: list[dict[str, Any]]):
    """Renderiza una fila de KPIs usando st.metric.

    Cada KPI: {
        "label": str,
        "value": str,                # ya formateado (usa formatters.py)
        "delta": str | None,         # opcional
        "delta_color": "normal"|"inverse"|"off",  # normal=verde si positivo
        "icon": str | None,          # opcional para prefijo
    }
    """
    if not kpis:
        return
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        with col:
            label = kpi.get("label", "")
            if kpi.get("icon"):
                label = f"{kpi['icon']} {label}"
            st.metric(
                label=label,
                value=kpi.get("value", "-"),
                delta=kpi.get("delta"),
                delta_color=kpi.get("delta_color", "normal"),
            )


def big_number_card(label: str, value: str, subtitle: str = "",
                    color: str = "#1B3A5C"):
    """Tarjeta grande estilo dashboard, para el Home."""
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color} 0%, {color}CC 100%);
        color: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 10px;">
        <div style="font-size: 13px; opacity: 0.85; margin-bottom: 6px;">{label}</div>
        <div style="font-size: 32px; font-weight: 700; line-height: 1.1;">{value}</div>
        <div style="font-size: 12px; opacity: 0.85; margin-top: 6px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)
