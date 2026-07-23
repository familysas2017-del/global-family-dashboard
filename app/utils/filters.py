"""Filtros globales del sidebar (fecha + categoría)."""
from __future__ import annotations
from typing import Any

import pandas as pd
import streamlit as st

from utils.data_loader import get_available_anio_mes, get_available_categorias


def render_sidebar_filters() -> dict[str, Any]:
    """Renderiza filtros y devuelve dict con selección.

    filters = {
        "anio_mes_inicio": "2026-01",
        "anio_mes_fin":    "2026-07",
        "categorias":       ["PAÑALES", ...],
    }
    """
    st.sidebar.title("Filtros")
    st.sidebar.markdown("---")

    # Corte a partir de 2026 — nunca mostrar 2024/2025 aunque exista en algún CSV
    meses = [m for m in get_available_anio_mes() if str(m) >= "2026-01"]
    cats  = get_available_categorias()

    if not meses:
        st.sidebar.warning("No hay datos 2026 cargados aún. Ejecuta el pipeline primero.")
        return {"anio_mes_inicio": None, "anio_mes_fin": None, "categorias": []}

    # Default: enero 2026 hasta el último mes disponible
    default_ini = "2026-01"
    default_fin = meses[-1]

    if "flt_ini" not in st.session_state:
        st.session_state["flt_ini"] = default_ini
        st.session_state["flt_fin"] = default_fin
        st.session_state["flt_cats"] = cats.copy()

    col1, col2 = st.sidebar.columns(2)
    with col1:
        ini = st.selectbox("Desde (año-mes)", meses,
                           index=meses.index(st.session_state["flt_ini"]) if st.session_state["flt_ini"] in meses else 0,
                           key="sel_ini")
    with col2:
        # Fin ≥ Inicio
        meses_fin = [m for m in meses if m >= ini]
        fin = st.selectbox("Hasta (año-mes)", meses_fin,
                           index=meses_fin.index(st.session_state["flt_fin"]) if st.session_state["flt_fin"] in meses_fin else len(meses_fin) - 1,
                           key="sel_fin")

    seleccionadas = st.sidebar.multiselect(
        "Categorías de producto",
        options=cats,
        default=st.session_state["flt_cats"],
        key="sel_cats",
    )
    if not seleccionadas:
        seleccionadas = cats  # si el usuario limpió todo, tratamos como "todas"

    if st.sidebar.button("Restablecer filtros"):
        st.session_state["flt_ini"] = default_ini
        st.session_state["flt_fin"] = default_fin
        st.session_state["flt_cats"] = cats.copy()
        st.rerun()

    st.session_state["flt_ini"] = ini
    st.session_state["flt_fin"] = fin
    st.session_state["flt_cats"] = seleccionadas

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Rango: **{ini}** → **{fin}**")
    st.sidebar.caption(f"Categorías: **{len(seleccionadas)}** de {len(cats)}")

    return {
        "anio_mes_inicio": ini,
        "anio_mes_fin": fin,
        "categorias": seleccionadas,
        "categorias_todas": cats,
    }


def apply_filters(df: pd.DataFrame, filters: dict, cat_col: str = "categoria_producto",
                  mes_col: str = "anio_mes") -> pd.DataFrame:
    """Aplica filtros de mes y categoría a un DataFrame. Silenciosamente ignora si no aplican."""
    if df.empty:
        return df
    out = df.copy()
    if mes_col in out.columns and filters.get("anio_mes_inicio") and filters.get("anio_mes_fin"):
        out = out[(out[mes_col] >= filters["anio_mes_inicio"]) &
                  (out[mes_col] <= filters["anio_mes_fin"])]
    if cat_col in out.columns and filters.get("categorias"):
        out = out[out[cat_col].isin(filters["categorias"])]
    return out


def periodo_anterior(filters: dict) -> dict:
    """Calcula el periodo anterior de igual longitud (para deltas)."""
    ini = filters.get("anio_mes_inicio")
    fin = filters.get("anio_mes_fin")
    if not ini or not fin:
        return {"anio_mes_inicio": None, "anio_mes_fin": None}
    ini_dt = pd.Period(ini, freq="M")
    fin_dt = pd.Period(fin, freq="M")
    n = (fin_dt - ini_dt).n + 1
    ini_prev = ini_dt - n
    fin_prev = ini_dt - 1
    return {
        "anio_mes_inicio": str(ini_prev),
        "anio_mes_fin": str(fin_prev),
        "categorias": filters.get("categorias"),
    }
