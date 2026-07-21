"""Carga cacheada de todos los CSVs producidos por el pipeline.

Todas las funciones usan @st.cache_data para evitar re-lecturas en cada rerun.
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd
import streamlit as st

# app/data/  → carpeta empaquetada para deploy (Streamlit Cloud lee de aquí)
# data/clean, data/metrics → carpetas del pipeline local (fallback en dev)
APP_ROOT     = Path(__file__).resolve().parent.parent       # .../app/
APP_DATA_DIR = APP_ROOT / "data"                             # .../app/data/  ← primera opción
PROJECT_ROOT = APP_ROOT.parent                               # .../GLOBAL FAMILY AI/
CLEAN_DIR    = PROJECT_ROOT / "data" / "clean"               # fallback dev
METRICS_DIR  = PROJECT_ROOT / "data" / "metrics"             # fallback dev

# Mapeo alias → (carpeta, filename, [cols_fecha]).
# Si un CSV no existe simplemente devuelve DataFrame vacío (para no romper la UI).
_REGISTRY: dict[str, tuple[str, str, list[str]]] = {
    # data/clean
    "fact_ventas":            ("clean",   "fact_ventas.csv",            ["fecha"]),
    "fact_cartera":           ("clean",   "fact_cartera.csv",           ["fecha_factura", "fecha_limite_pago"]),
    "fact_cxp_nacional":      ("clean",   "fact_cxp_nacional.csv",      ["fecha_factura", "fecha_vencimiento"]),
    "fact_cxp_internacional": ("clean",   "fact_cxp_internacional.csv", ["fecha_factura", "fecha_vencimiento"]),
    "fact_gastos":            ("clean",   "fact_gastos.csv",            ["fecha"]),
    "fact_ventas_vendedor":   ("clean",   "fact_ventas_vendedor.csv",   []),
    "fact_deuda_jeison":      ("clean",   "fact_deuda_jeison.csv",      ["fecha_cuota"]),
    "dim_inventario":         ("clean",   "dim_inventario.csv",         []),
    "dim_clientes":           ("clean",   "dim_clientes.csv",           ["primera_compra", "ultima_compra"]),
    "dim_productos":          ("clean",   "dim_productos.csv",          ["primera_venta", "ultima_venta"]),
    "dim_proveedores":        ("clean",   "dim_proveedores.csv",        []),
    "dim_calendario":         ("clean",   "dim_calendario.csv",         ["fecha"]),
    "costo_ventas_er":        ("clean",   "costo_ventas_er.csv",        []),
    # data/metrics
    "venta_mensual":                  ("metrics", "venta_mensual.csv",                  []),
    "venta_x_categoria_mes":          ("metrics", "venta_x_categoria_mes.csv",          []),
    "categorias_crecimiento":         ("metrics", "categorias_crecimiento.csv",         []),
    "utilidad_bruta_mensual":         ("metrics", "utilidad_bruta_mensual.csv",         []),
    "utilidad_bruta_x_categoria":     ("metrics", "utilidad_bruta_x_categoria.csv",     []),
    "ranking_margen_categoria":       ("metrics", "ranking_margen_categoria.csv",       []),
    "rotacion_x_categoria":           ("metrics", "rotacion_x_categoria.csv",           []),
    "escalera_rotacion_productos":    ("metrics", "escalera_rotacion_productos.csv",    ["ultima_venta"]),
    "working_capital":                ("metrics", "working_capital.csv",                ["fecha_calculo"]),
    "dias_cartera_resumen":           ("metrics", "dias_cartera_resumen.csv",           []),
    "dias_cartera_por_cliente":       ("metrics", "dias_cartera_por_cliente.csv",       []),
    "dias_cartera_aging":             ("metrics", "dias_cartera_aging.csv",             []),
    "dias_cartera_vencidas_gt90":     ("metrics", "dias_cartera_vencidas_gt90.csv",     ["fecha_limite_pago"]),
    "dias_cxp_resumen":               ("metrics", "dias_cxp_resumen.csv",               []),
    "dias_cxp_por_proveedor_nal":     ("metrics", "dias_cxp_por_proveedor_nal.csv",     []),
    "dias_cxp_por_proveedor_int":     ("metrics", "dias_cxp_por_proveedor_int.csv",     []),
    "dias_cxp_aging_nacional":        ("metrics", "dias_cxp_aging_nacional.csv",        []),
    "dias_cxp_proximos_vencimientos": ("metrics", "dias_cxp_proximos_vencimientos.csv", ["fecha_vencimiento"]),
    "gastos_mensual":                 ("metrics", "gastos_mensual.csv",                 []),
    "gastos_x_categoria":             ("metrics", "gastos_x_categoria.csv",             []),
    "gastos_fijo_variable":           ("metrics", "gastos_fijo_variable.csv",           []),
    "gastos_operacional_no_operacional": ("metrics", "gastos_operacional_no_operacional.csv", []),
    "margen_x_cliente":               ("metrics", "margen_x_cliente.csv",               ["ultima_compra", "primera_compra"]),
    "margen_x_producto":              ("metrics", "margen_x_producto.csv",              []),
    "fletes_vs_ventas":               ("metrics", "fletes_vs_ventas.csv",               []),
    "ventas_x_vendedor":              ("metrics", "ventas_x_vendedor.csv",              []),
}


def _resolve_path(carpeta: str, filename: str) -> Path | None:
    """Busca primero en app/data/ (deploy); si no está, en data/clean o data/metrics (dev)."""
    p_deploy = APP_DATA_DIR / filename
    if p_deploy.exists():
        return p_deploy
    p_fallback = (CLEAN_DIR if carpeta == "clean" else METRICS_DIR) / filename
    if p_fallback.exists():
        return p_fallback
    return None


@st.cache_data(show_spinner=False)
def get_data(alias: str) -> pd.DataFrame:
    """Devuelve el DataFrame para un alias registrado. Vacío si no existe."""
    if alias not in _REGISTRY:
        return pd.DataFrame()
    carpeta, filename, cols_fecha = _REGISTRY[alias]
    path = _resolve_path(carpeta, filename)
    if path is None:
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    for c in cols_fecha:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def get_last_data_date() -> str:
    """Última fecha de venta registrada en fact_ventas — usada como 'datos al'."""
    df = get_data("fact_ventas")
    if df.empty or "fecha" not in df.columns:
        return "s/d"
    d = pd.to_datetime(df["fecha"]).max()
    return d.strftime("%Y-%m-%d") if pd.notna(d) else "s/d"


@st.cache_data(show_spinner=False)
def get_available_anio_mes() -> list[str]:
    """Meses únicos disponibles en fact_ventas, ordenados asc."""
    df = get_data("fact_ventas")
    if df.empty or "anio_mes" not in df.columns:
        return []
    return sorted(df["anio_mes"].dropna().unique().tolist())


@st.cache_data(show_spinner=False)
def get_available_categorias() -> list[str]:
    """Categorías únicas."""
    df = get_data("fact_ventas")
    if df.empty or "categoria_producto" not in df.columns:
        return []
    return sorted(df["categoria_producto"].dropna().unique().tolist())
