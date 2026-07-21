"""
Genera las tablas dimensionales a partir de fact_ventas + inventario + cxp.
Guarda en data/clean/.
"""
from __future__ import annotations
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from config import CLEAN_DIR

log = logging.getLogger(__name__)


def _read(name: str) -> pd.DataFrame:
    p = CLEAN_DIR / name
    if not p.exists():
        raise FileNotFoundError(p)
    return pd.read_csv(p, low_memory=False)


def _save(df: pd.DataFrame, name: str):
    p = CLEAN_DIR / name
    df.to_csv(p, index=False, encoding="utf-8")
    log.info("  → %s (%d filas × %d cols)", name, len(df), len(df.columns))


# =========================================================
# dim_clientes
# =========================================================
def build_dim_clientes(ventas: pd.DataFrame):
    log.info("dim_clientes…")
    ventas["fecha"] = pd.to_datetime(ventas["fecha"], errors="coerce")
    g = ventas.groupby(["ident_cliente", "cliente"], dropna=False).agg(
        primera_compra=("fecha", "min"),
        ultima_compra=("fecha", "max"),
        total_facturas=("factura", "nunique"),
        total_lineas=("factura", "count"),
        cliente_generico=("cliente_generico", "first"),
    ).reset_index()
    g = g.rename(columns={"ident_cliente": "id_cliente"})
    _save(g, "dim_clientes.csv")


# =========================================================
# dim_productos
# =========================================================
def build_dim_productos(ventas: pd.DataFrame):
    log.info("dim_productos…")
    g = ventas.groupby(["cod_interno"], dropna=False).agg(
        descripcion=("descripcion_producto", "first"),
        cod_barras=("cod_barras", "first"),
        categoria_producto=("categoria_producto", "first"),
        marca_proveedor=("proveedor_marca", "first"),
        primera_venta=("fecha", "min"),
        ultima_venta=("fecha", "max"),
        unidades_hist=("cantidad", "sum"),
        ingresos_hist=("total", "sum"),
    ).reset_index()
    _save(g, "dim_productos.csv")


# =========================================================
# dim_proveedores (nal + int)
# =========================================================
def build_dim_proveedores():
    log.info("dim_proveedores…")
    frames = []
    try:
        nac = _read("fact_cxp_nacional.csv")
        agg_n = nac.groupby("proveedor").agg(
            total_compras=("valor_total", "sum"),
            n_facturas=("valor_total", "count"),
            saldo_pendiente=("saldo_pendiente", "sum"),
        ).reset_index()
        agg_n["tipo"] = "nacional"
        frames.append(agg_n)
    except FileNotFoundError:
        log.warning("no hay fact_cxp_nacional")
    try:
        internacional = _read("fact_cxp_internacional.csv")
        agg_i = internacional.groupby("proveedor").agg(
            total_compras=("valor_en_sistema", "sum"),
            n_facturas=("valor_en_sistema", "count"),
            saldo_pendiente=("saldo_pendiente_cop", "sum"),
        ).reset_index()
        agg_i["tipo"] = "internacional"
        frames.append(agg_i)
    except FileNotFoundError:
        log.warning("no hay fact_cxp_internacional")
    if not frames:
        return
    df = pd.concat(frames, ignore_index=True)
    _save(df, "dim_proveedores.csv")


# =========================================================
# dim_calendario
# =========================================================
def build_dim_calendario(ventas: pd.DataFrame):
    log.info("dim_calendario…")
    ventas["fecha"] = pd.to_datetime(ventas["fecha"], errors="coerce")
    d0 = ventas["fecha"].min()
    d1 = pd.Timestamp.today().normalize() + pd.Timedelta(days=180)  # colchón futuro
    fechas = pd.date_range(d0, d1, freq="D")
    df = pd.DataFrame({"fecha": fechas})
    df["anio"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["nombre_mes"] = df["fecha"].dt.strftime("%B")
    df["trimestre"] = df["fecha"].dt.quarter
    df["semana"] = df["fecha"].dt.isocalendar().week.astype(int)
    df["dia_semana"] = df["fecha"].dt.day_name()
    df["anio_mes"] = df["fecha"].dt.to_period("M").astype(str)
    _save(df, "dim_calendario.csv")


def run():
    log.info("=== BUILD MODEL (dimensionales) ===")
    ventas = _read("fact_ventas.csv")
    build_dim_clientes(ventas)
    build_dim_productos(ventas)
    build_dim_proveedores()
    build_dim_calendario(ventas)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
