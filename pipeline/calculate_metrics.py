"""
Calcula todas las métricas de negocio y las guarda en data/metrics/ como CSV.
11 grupos, 22 archivos objetivo. Cada métrica en su propia función.
"""
from __future__ import annotations
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    CLEAN_DIR, METRICS_DIR, VENTANA_3M_DIAS, VENTANA_6M_DIAS,
    META_ANUAL_2026,
)

log = logging.getLogger(__name__)


# =========================================================
# UTILIDADES
# =========================================================
def _read(name: str) -> pd.DataFrame:
    p = CLEAN_DIR / name
    if not p.exists():
        raise FileNotFoundError(p)
    df = pd.read_csv(p, low_memory=False)
    for c in df.columns:
        if "fecha" in c or c == "primera_compra" or c == "ultima_compra" or c == "ultima_venta" or c == "primera_venta":
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def _save(df: pd.DataFrame, name: str):
    p = METRICS_DIR / name
    df.to_csv(p, index=False, encoding="utf-8")
    log.info("  → %s (%d filas × %d cols)", name, len(df), len(df.columns))


def _pct(x, y):
    return np.where(pd.Series(y).fillna(0) != 0, x / y, np.nan)


# =========================================================
# GRUPO 1: VENTAS
# =========================================================
def g1_ventas():
    log.info("[G1] Ventas (venta_neta = post-devoluciones prorrateadas)")
    v = _read("fact_ventas.csv")
    if "venta_neta_linea" not in v.columns:
        v["venta_neta_linea"] = v["total_venta"]

    # 1.1 venta_mensual
    m = v.groupby("anio_mes").agg(
        venta_bruta=("total_venta", "sum"),
        venta_neta=("venta_neta_linea", "sum"),
        unidades=("cantidad", "sum"),
        facturas=("factura", "nunique"),
    ).reset_index().sort_values("anio_mes")
    m["devoluciones"] = (m["venta_bruta"] - m["venta_neta"]).round(0)
    m["ticket_promedio"] = (m["venta_neta"] / m["facturas"]).round(0)
    _save(m, "venta_mensual.csv")

    # 1.2 venta_x_categoria_mes con crecimiento
    c = v.groupby(["anio_mes", "categoria_producto"]).agg(
        venta_neta=("venta_neta_linea", "sum"),
        venta_bruta=("total_venta", "sum"),
        unidades=("cantidad", "sum"),
    ).reset_index().sort_values(["categoria_producto", "anio_mes"])
    c["crecimiento_pct_mom"] = (
        c.groupby("categoria_producto")["venta_neta"]
         .pct_change().round(4)
    )
    _save(c, "venta_x_categoria_mes.csv")

    # 1.3 categorias_crecimiento (últimos 3 vs previos 3)
    v["fecha"] = pd.to_datetime(v["fecha"], errors="coerce")
    max_d = v["fecha"].max()
    last3   = v[v["fecha"] >  max_d - pd.Timedelta(days=VENTANA_3M_DIAS)]
    prev3   = v[(v["fecha"] >  max_d - pd.Timedelta(days=VENTANA_6M_DIAS)) &
                (v["fecha"] <= max_d - pd.Timedelta(days=VENTANA_3M_DIAS))]
    a = last3.groupby("categoria_producto")["venta_neta_linea"].sum().rename("venta_3m_recientes")
    b = prev3.groupby("categoria_producto")["venta_neta_linea"].sum().rename("venta_3m_previos")
    r = pd.concat([a, b], axis=1).reset_index().fillna(0)
    r["crecimiento_pct"] = np.where(r["venta_3m_previos"] > 0,
                                    (r["venta_3m_recientes"] - r["venta_3m_previos"]) / r["venta_3m_previos"],
                                    np.nan)

    def diag(g):
        if pd.isna(g): return "SIN_BASE"
        if g >  0.05:  return "CRECIENDO"
        if g < -0.05:  return "DECRECIENDO"
        return "ESTABLE"
    r["tendencia"] = r["crecimiento_pct"].map(diag)
    r = r.sort_values("crecimiento_pct", ascending=False)
    _save(r, "categorias_crecimiento.csv")


# =========================================================
# GRUPO 2: UTILIDAD BRUTA
# =========================================================
def g2_utilidad_bruta():
    log.info("[G2] Utilidad Bruta (base = Ventas NETAS, alineado con reporte oficial)")
    v = _read("fact_ventas.csv")
    # Ventas Netas por línea = total_venta - devolucion_prorrateada (fuente: correct_costs)
    if "venta_neta_linea" not in v.columns:
        v["venta_neta_linea"] = v["total_venta"]  # fallback si no se corrigieron costos

    def ub_agg(g):
        return pd.Series({
            "venta_bruta": g["total_venta"].sum(),
            "venta_total": g["venta_neta_linea"].sum(),  # "venta_total" ahora = neta (base del margen)
            "costo_total": g["costo_total_linea"].sum(),
        })

    # 2.1 mensual
    m = v.groupby("anio_mes").apply(ub_agg).reset_index()
    m["utilidad_bruta"] = (m["venta_total"] - m["costo_total"]).round(0)
    m["margen_bruto_pct"] = np.where(m["venta_total"] > 0,
                                     (m["utilidad_bruta"] / m["venta_total"]).round(4), np.nan)
    _save(m, "utilidad_bruta_mensual.csv")

    # 2.2 x categoria x mes
    c = v.groupby(["anio_mes", "categoria_producto"]).apply(ub_agg).reset_index()
    c["utilidad_bruta"] = (c["venta_total"] - c["costo_total"]).round(0)
    c["margen_bruto_pct"] = np.where(c["venta_total"] > 0,
                                     (c["utilidad_bruta"] / c["venta_total"]).round(4), np.nan)
    _save(c, "utilidad_bruta_x_categoria.csv")

    # 2.3 ranking margen por categoria
    r = v.groupby("categoria_producto").apply(ub_agg).reset_index()
    r["utilidad_bruta"] = (r["venta_total"] - r["costo_total"]).round(0)
    r["margen_bruto_pct"] = np.where(r["venta_total"] > 0,
                                     (r["utilidad_bruta"] / r["venta_total"]).round(4), np.nan)
    r = r.sort_values("margen_bruto_pct", ascending=False)
    _save(r, "ranking_margen_categoria.csv")


# =========================================================
# GRUPO 3: ROTACIÓN
# =========================================================
def g3_rotacion():
    log.info("[G3] Rotación")
    v = _read("fact_ventas.csv")
    v["fecha"] = pd.to_datetime(v["fecha"], errors="coerce")
    inv = _read("dim_inventario.csv")

    max_d = v["fecha"].max()
    last6 = v[v["fecha"] > max_d - pd.Timedelta(days=VENTANA_6M_DIAS)]

    # 3.1 rotacion x categoria
    # inventario_promedio por categoria: aproximado con el stock actual valuado
    inv_cat = inv.groupby("categoria_producto").agg(
        inventario_costo=("costo_total_inventario", "sum")
    ).reset_index()
    costo_v_cat = last6.groupby("categoria_producto").agg(
        costo_ventas_6m=("costo_total_linea", "sum")
    ).reset_index()
    r = inv_cat.merge(costo_v_cat, on="categoria_producto", how="outer").fillna(0)
    # anualizamos costo_ventas_6m * 2 para tener costo_ventas_12m aproximado
    r["costo_ventas_anualizado"] = r["costo_ventas_6m"] * 2
    r["rotacion"] = np.where(r["inventario_costo"] > 0,
                             (r["costo_ventas_anualizado"] / r["inventario_costo"]).round(2),
                             np.nan)
    r["dias_inventario"] = np.where(r["rotacion"] > 0, (365 / r["rotacion"]).round(0), np.nan)
    r = r.sort_values("rotacion", ascending=False)
    _save(r, "rotacion_x_categoria.csv")

    # 3.2 escalera_rotacion_productos
    v_q = v[v["fecha"] > max_d - pd.Timedelta(days=90)]
    ult_venta = v.groupby("cod_interno").agg(
        ultima_venta=("fecha", "max"),
        venta_total_hist=("total", "sum"),
    ).reset_index()
    v_q_agg = v_q.groupby("cod_interno").agg(
        cantidad_ultimo_trimestre=("cantidad", "sum")
    ).reset_index()
    # promedio mensual = ultimo_trimestre / 3
    prod_desc = v.groupby("cod_interno").agg(
        descripcion=("descripcion_producto", "first"),
        categoria_producto=("categoria_producto", "first"),
    ).reset_index()
    # join con inventario por descripción (no hay cod interno en Inv)
    # normalizamos descripción para el join
    inv["_key"] = inv["producto"].str.upper().str.strip()
    prod_desc["_key"] = prod_desc["descripcion"].str.upper().str.strip()
    inv_stock = inv[["_key", "stock_actual", "costo_total_inventario"]].copy()
    esc = prod_desc.merge(ult_venta, on="cod_interno", how="left") \
                   .merge(v_q_agg, on="cod_interno", how="left") \
                   .merge(inv_stock, on="_key", how="left")

    esc["cantidad_ultimo_trimestre"] = esc["cantidad_ultimo_trimestre"].fillna(0)
    esc["dias_sin_venta"] = (max_d - esc["ultima_venta"]).dt.days.fillna(9999).astype(int)

    def clasificar(d):
        if d <= 30: return "ACTIVO"
        if d <= 90: return "DORMIDO"
        return "MUERTO"
    esc["clasificacion_rotacion"] = esc["dias_sin_venta"].map(clasificar)

    esc["promedio_venta_mensual"] = (esc["cantidad_ultimo_trimestre"] / 3).round(2)
    esc["meses_inventario"] = np.where(
        esc["promedio_venta_mensual"] > 0,
        (esc["stock_actual"].fillna(0) / esc["promedio_venta_mensual"]).round(1),
        np.nan,
    )
    esc = esc.drop(columns=["_key"])
    esc = esc.sort_values(
        ["clasificacion_rotacion", "costo_total_inventario"],
        ascending=[True, False],
    )
    _save(esc, "escalera_rotacion_productos.csv")


# =========================================================
# GRUPO 4: WORKING CAPITAL
# =========================================================
def g4_working_capital(fecha_hoy: pd.Timestamp):
    log.info("[G4] Working Capital")
    cartera = _read("fact_cartera.csv")
    inv = _read("dim_inventario.csv")
    cxp_n = _read("fact_cxp_nacional.csv")
    cxp_i = _read("fact_cxp_internacional.csv")
    jeison = _read("fact_deuda_jeison.csv")
    v = _read("fact_ventas.csv"); v["fecha"] = pd.to_datetime(v["fecha"], errors="coerce")
    g = _read("fact_gastos.csv"); g["fecha"] = pd.to_datetime(g["fecha"], errors="coerce")

    cartera_total = float(cartera["saldo_pendiente"].sum())
    inventario_total = float(inv["costo_total_inventario"].sum())
    cxp_n_total = float(cxp_n["saldo_pendiente"].clip(lower=0).sum())
    cxp_i_total = float(cxp_i["saldo_pendiente_cop"].fillna(0).clip(lower=0).sum())

    # Cuotas Jeison próximos 12 meses
    fut = jeison[(jeison["estado"] == "pendiente_futura") &
                 (pd.to_datetime(jeison["fecha_cuota"], errors="coerce") <=
                  fecha_hoy + pd.Timedelta(days=365))]
    cuotas_jeison_12m = float(fut["valor_cuota"].fillna(0).sum())

    # caja estimada
    max_d = v["fecha"].max()
    v_ult_mes = v[v["fecha"] > max_d - pd.Timedelta(days=30)]["total"].sum()
    g_ult_mes = g[g["fecha"] > max_d - pd.Timedelta(days=30)]["valor_cop"].sum()
    recaudo_pct = 0.85  # 85% de la venta se recauda en el mes (supuesto)
    caja_estimada = v_ult_mes * recaudo_pct - g_ult_mes
    caja_es_estimada = True

    activo = cartera_total + inventario_total + caja_estimada
    pasivo = cxp_n_total + cxp_i_total + cuotas_jeison_12m
    kt = activo - pasivo
    rc = activo / pasivo if pasivo > 0 else np.nan

    df = pd.DataFrame([{
        "fecha_calculo": fecha_hoy.date(),
        "cartera_total": cartera_total,
        "inventario_total": inventario_total,
        "caja_estimada": round(caja_estimada, 0),
        "caja_es_estimada": caja_es_estimada,
        "activo_corriente": round(activo, 0),
        "cxp_nacional_total": cxp_n_total,
        "cxp_internacional_total": cxp_i_total,
        "cuotas_jeison_12m": cuotas_jeison_12m,
        "pasivo_corriente": round(pasivo, 0),
        "capital_de_trabajo": round(kt, 0),
        "razon_corriente": round(rc, 2) if pasivo > 0 else None,
    }])
    _save(df, "working_capital.csv")


# =========================================================
# GRUPO 5: DÍAS DE CARTERA (DSO)
# =========================================================
def g5_dias_cartera(fecha_hoy: pd.Timestamp):
    log.info("[G5] Días de Cartera (DSO)")
    cartera = _read("fact_cartera.csv")
    v = _read("fact_ventas.csv"); v["fecha"] = pd.to_datetime(v["fecha"], errors="coerce")

    cartera_total = float(cartera["saldo_pendiente"].sum())
    max_d = v["fecha"].max()
    ventas_90 = float(v[v["fecha"] > max_d - pd.Timedelta(days=90)]["total"].sum())
    dso_global = round(cartera_total / ventas_90 * 90, 1) if ventas_90 > 0 else None

    # DSO por cliente (top 20 con más días)
    by_cli = cartera.groupby("cliente").agg(
        saldo_pendiente=("saldo_pendiente", "sum"),
        dias_prom_vencido=("dias_vencido", "mean"),
        n_facturas_pendientes=("num_factura", "count"),
    ).reset_index().sort_values("dias_prom_vencido", ascending=False).head(20)

    # Aging total
    aging = cartera.groupby("tramo_aging").agg(
        monto=("saldo_pendiente", "sum"),
        n_facturas=("saldo_pendiente", "count"),
    ).reset_index()
    aging["pct_total"] = (aging["monto"] / aging["monto"].sum()).round(4)

    # Facturas vencidas > 90
    vencidas = cartera[cartera["dias_vencido"] > 90][
        ["num_factura", "cliente", "saldo_pendiente", "dias_vencido", "fecha_limite_pago"]
    ].sort_values("saldo_pendiente", ascending=False)

    # Guardamos las 3 en un único CSV largo con "seccion"
    df1 = pd.DataFrame([{
        "seccion": "resumen", "clave": "DSO global (días)", "valor": dso_global,
        "cartera_total_cop": cartera_total, "ventas_90d_cop": ventas_90,
    }])
    df2 = by_cli.assign(seccion="dso_por_cliente_top20")
    df3 = aging.assign(seccion="aging_total")
    df4 = vencidas.assign(seccion="alerta_vencidas_>90d")

    # export en dataframes separados también, para consumo directo del dashboard
    _save(df1, "dias_cartera_resumen.csv")
    _save(df2, "dias_cartera_por_cliente.csv")
    _save(df3, "dias_cartera_aging.csv")
    _save(df4, "dias_cartera_vencidas_gt90.csv")


# =========================================================
# GRUPO 6: DÍAS DE CxP (DPO)
# =========================================================
def g6_dias_cxp(fecha_hoy: pd.Timestamp):
    log.info("[G6] Días de CxP (DPO)")
    cxp_n = _read("fact_cxp_nacional.csv")
    cxp_i = _read("fact_cxp_internacional.csv")

    # Compras últimos 90 días
    cxp_n["fecha_factura"] = pd.to_datetime(cxp_n["fecha_factura"], errors="coerce")
    cxp_i["fecha_factura"] = pd.to_datetime(cxp_i["fecha_factura"], errors="coerce")
    comp_n_90 = cxp_n[cxp_n["fecha_factura"] > fecha_hoy - pd.Timedelta(days=90)]["valor_total"].sum()
    comp_i_90 = cxp_i[cxp_i["fecha_factura"] > fecha_hoy - pd.Timedelta(days=90)]["valor_en_sistema"].sum()

    cxp_n_saldo = cxp_n["saldo_pendiente"].clip(lower=0).sum()
    cxp_i_saldo = cxp_i["saldo_pendiente_cop"].fillna(0).clip(lower=0).sum()

    dpo_n = round(cxp_n_saldo / comp_n_90 * 90, 1) if comp_n_90 > 0 else None
    dpo_i = round(cxp_i_saldo / comp_i_90 * 90, 1) if comp_i_90 > 0 else None
    dpo_g = round((cxp_n_saldo + cxp_i_saldo) / (comp_n_90 + comp_i_90) * 90, 1) if (comp_n_90 + comp_i_90) > 0 else None

    resumen = pd.DataFrame([
        {"tipo": "nacional",        "saldo_pendiente": cxp_n_saldo, "compras_90d": comp_n_90, "dpo": dpo_n},
        {"tipo": "internacional",   "saldo_pendiente": cxp_i_saldo, "compras_90d": comp_i_90, "dpo": dpo_i},
        {"tipo": "global",          "saldo_pendiente": cxp_n_saldo + cxp_i_saldo,
         "compras_90d": comp_n_90 + comp_i_90, "dpo": dpo_g},
    ])
    _save(resumen, "dias_cxp_resumen.csv")

    # DPO por proveedor (nacional)
    prov_n = cxp_n.groupby("proveedor").agg(
        saldo_pendiente=("saldo_pendiente", "sum"),
        compras=("valor_total", "sum"),
        n_facturas=("valor_total", "count"),
    ).reset_index()
    prov_n["dpo"] = np.where(prov_n["compras"] > 0,
                             (prov_n["saldo_pendiente"] / prov_n["compras"] * 90).round(1), np.nan)
    prov_n = prov_n.sort_values("saldo_pendiente", ascending=False)
    _save(prov_n, "dias_cxp_por_proveedor_nal.csv")

    # DPO por proveedor (internacional)
    prov_i = cxp_i.groupby("proveedor").agg(
        saldo_pendiente=("saldo_pendiente_cop", "sum"),
        compras=("valor_en_sistema", "sum"),
        n_facturas=("valor_en_sistema", "count"),
    ).reset_index()
    prov_i["dpo"] = np.where(prov_i["compras"] > 0,
                             (prov_i["saldo_pendiente"] / prov_i["compras"] * 90).round(1), np.nan)
    prov_i = prov_i.sort_values("saldo_pendiente", ascending=False)
    _save(prov_i, "dias_cxp_por_proveedor_int.csv")

    # Aging CxP nacional
    aging_n = cxp_n.groupby("tramo_aging").agg(
        monto=("saldo_pendiente", "sum"),
        n=("saldo_pendiente", "count"),
    ).reset_index()
    aging_n["pct_total"] = (aging_n["monto"] / aging_n["monto"].sum()).round(4)
    _save(aging_n, "dias_cxp_aging_nacional.csv")

    # Próximos vencimientos (nacional + internacional consolidado)
    cols_n = ["proveedor", "fecha_vencimiento", "saldo_pendiente"]
    cols_i = ["proveedor", "fecha_vencimiento", "saldo_pendiente_cop"]
    nxt_n = cxp_n[cxp_n["saldo_pendiente"] > 0][cols_n].copy()
    nxt_i = cxp_i[cxp_i["saldo_pendiente_cop"].fillna(0) > 0][cols_i].rename(
        columns={"saldo_pendiente_cop": "saldo_pendiente"}
    ).copy()
    nxt = pd.concat([nxt_n.assign(tipo="nacional"), nxt_i.assign(tipo="internacional")], ignore_index=True)
    nxt["fecha_vencimiento"] = pd.to_datetime(nxt["fecha_vencimiento"], errors="coerce")
    nxt["dias_al_vencimiento"] = (nxt["fecha_vencimiento"] - fecha_hoy).dt.days
    def bucket(d):
        if pd.isna(d): return "sin_fecha"
        if d < 0: return "vencido"
        if d <= 7: return "esta_semana"
        if d <= 14: return "prox_2_semanas"
        if d <= 30: return "prox_mes"
        return "posterior"
    nxt["ventana"] = nxt["dias_al_vencimiento"].map(bucket)
    nxt = nxt.sort_values("fecha_vencimiento")
    _save(nxt, "dias_cxp_proximos_vencimientos.csv")


# =========================================================
# GRUPO 7: GASTOS
# =========================================================
def g7_gastos():
    log.info("[G7] Gastos")
    g = _read("fact_gastos.csv")
    v = _read("fact_ventas.csv")

    # 7.1 mensual total
    m = g.groupby("anio_mes").agg(total_gastos=("valor_cop", "sum"),
                                   n_registros=("valor_cop", "count")).reset_index().sort_values("anio_mes")
    _save(m, "gastos_mensual.csv")

    # 7.2 por tipo x mes
    t = g.groupby(["anio_mes", "tipo"]).agg(
        valor=("valor_cop", "sum"), n=("valor_cop", "count")
    ).reset_index().sort_values(["anio_mes", "valor"], ascending=[True, False])
    _save(t, "gastos_x_categoria.csv")

    # 7.3 fijo vs variable con % sobre ventas
    fv = g.groupby(["anio_mes", "clasificacion_fx"])["valor_cop"].sum().unstack(fill_value=0).reset_index()
    for col in ("fijo", "variable"):
        if col not in fv.columns:
            fv[col] = 0
    vm = v.groupby("anio_mes")["total"].sum().rename("ventas_totales").reset_index()
    fv = fv.merge(vm, on="anio_mes", how="left")
    fv["pct_fijo_sobre_ventas"] = np.where(fv["ventas_totales"] > 0,
                                            (fv["fijo"] / fv["ventas_totales"]).round(4), np.nan)
    fv["pct_variable_sobre_ventas"] = np.where(fv["ventas_totales"] > 0,
                                                (fv["variable"] / fv["ventas_totales"]).round(4), np.nan)
    _save(fv.sort_values("anio_mes"), "gastos_fijo_variable.csv")

    # 7.4 operacional vs no_operacional
    op = g.groupby(["anio_mes", "clasificacion_op"])["valor_cop"].sum().unstack(fill_value=0).reset_index()
    _save(op.sort_values("anio_mes"), "gastos_operacional_no_operacional.csv")


# =========================================================
# GRUPO 8: MARGEN POR CLIENTE
# =========================================================
def g8_margen_cliente(fecha_hoy: pd.Timestamp):
    log.info("[G8] Margen por Cliente (base = Ventas NETAS)")
    v = _read("fact_ventas.csv")
    v["fecha"] = pd.to_datetime(v["fecha"], errors="coerce")
    if "venta_neta_linea" not in v.columns:
        v["venta_neta_linea"] = v["total_venta"]
    # Agrupamos por ident_cliente (identidad única). El nombre puede variar por typos → usamos el
    # más usado por identidad para evitar duplicados de la misma persona con nombres ligeramente distintos.
    nombre_por_id = (v.groupby("ident_cliente")["cliente"]
                      .agg(lambda s: s.value_counts().idxmax() if len(s) else None))
    g = v.groupby(["ident_cliente"], dropna=False).agg(
        venta_total=("venta_neta_linea", "sum"),   # ← Ventas Netas
        venta_bruta=("total_venta", "sum"),
        costo_total=("costo_total_linea", "sum"),
        cantidad_facturas=("factura", "nunique"),
        ultima_compra=("fecha", "max"),
        primera_compra=("fecha", "min"),
        generico=("cliente_generico", "first"),
    ).reset_index()
    g["cliente"] = g["ident_cliente"].map(nombre_por_id)
    g = g[["ident_cliente", "cliente", "venta_total", "venta_bruta", "costo_total", "cantidad_facturas",
           "ultima_compra", "primera_compra", "generico"]]
    g["margen_bruto"] = (g["venta_total"] - g["costo_total"]).round(0)
    g["margen_bruto_pct"] = np.where(g["venta_total"] > 0,
                                      (g["margen_bruto"] / g["venta_total"]).round(4), np.nan)
    g["ticket_promedio"] = (g["venta_total"] / g["cantidad_facturas"]).round(0)
    g["dias_sin_comprar"] = (fecha_hoy - g["ultima_compra"]).dt.days.fillna(9999).astype(int)

    # ABC sobre no-genéricos, por facturación acumulada
    real = g[~g["generico"].fillna(False)].sort_values("venta_total", ascending=False).reset_index(drop=True).copy()
    tot = real["venta_total"].sum()
    real["acum_pct"] = real["venta_total"].cumsum() / tot
    def abc(p):
        if p <= 0.80: return "A"
        if p <= 0.95: return "B"
        return "C"
    real["clasificacion_abc"] = real["acum_pct"].map(abc)
    g = g.merge(real[["ident_cliente", "clasificacion_abc"]], on="ident_cliente", how="left")

    g = g.sort_values("margen_bruto_pct", ascending=False)
    _save(g, "margen_x_cliente.csv")


# =========================================================
# GRUPO 9: MARGEN POR PRODUCTO
# =========================================================
def g9_margen_producto():
    log.info("[G9] Margen por Producto (base = Ventas NETAS)")
    v = _read("fact_ventas.csv")
    if "venta_neta_linea" not in v.columns:
        v["venta_neta_linea"] = v["total_venta"]
    g = v.groupby(["cod_interno"], dropna=False).agg(
        descripcion=("descripcion_producto", "first"),
        categoria=("categoria_producto", "first"),
        marca_proveedor=("proveedor_marca", "first"),
        venta_total=("venta_neta_linea", "sum"),   # ← Ventas Netas
        venta_bruta=("total_venta", "sum"),
        costo_total=("costo_total_linea", "sum"),
        cantidad_vendida=("cantidad", "sum"),
    ).reset_index()
    g["margen_bruto"] = (g["venta_total"] - g["costo_total"]).round(0)
    g["margen_bruto_pct"] = np.where(g["venta_total"] > 0,
                                      (g["margen_bruto"] / g["venta_total"]).round(4), np.nan)
    g["precio_venta_promedio"] = np.where(g["cantidad_vendida"] > 0,
                                           (g["venta_total"] / g["cantidad_vendida"]).round(0), np.nan)
    g["costo_promedio"] = np.where(g["cantidad_vendida"] > 0,
                                    (g["costo_total"] / g["cantidad_vendida"]).round(0), np.nan)
    # ABC sobre facturación
    g = g.sort_values("venta_total", ascending=False).reset_index(drop=True)
    total = g["venta_total"].sum()
    g["acum_pct"] = g["venta_total"].cumsum() / total
    def abc(p):
        if p <= 0.80: return "A"
        if p <= 0.95: return "B"
        return "C"
    g["clasificacion_abc"] = g["acum_pct"].map(abc)
    g = g.sort_values("margen_bruto_pct", ascending=False)
    _save(g, "margen_x_producto.csv")


# =========================================================
# GRUPO 10: FLETES / VENTAS
# =========================================================
def g10_fletes_vs_ventas():
    log.info("[G10] Fletes vs Ventas")
    g = _read("fact_gastos.csv")
    v = _read("fact_ventas.csv")
    def in_any(t, needles):
        if not isinstance(t, str): return False
        tl = t.lower()
        return any(n.lower() in tl for n in needles)
    flete_nal_keys = ["Fletes Nacionales", "Fletes Locales", "Viáticos Logística"]
    flete_int_keys = ["Viajes China", "Viajes Panamá", "Comisiones Swift"]

    g["flete_nal"]  = g["valor_cop"] * g["tipo"].map(lambda t: in_any(t, flete_nal_keys)).astype(int)
    g["flete_imp"]  = g["valor_cop"] * g["tipo"].map(lambda t: in_any(t, flete_int_keys)).astype(int)

    fm = g.groupby("anio_mes").agg(
        flete_nacional=("flete_nal", "sum"),
        flete_importacion=("flete_imp", "sum"),
    ).reset_index()

    _vcol = "venta_neta_linea" if "venta_neta_linea" in v.columns else "total_venta"
    vm = v.groupby("anio_mes")[_vcol].sum().rename("ventas_total").reset_index()
    r = fm.merge(vm, on="anio_mes", how="outer").fillna(0).sort_values("anio_mes")
    r["flete_total"] = r["flete_nacional"] + r["flete_importacion"]
    r["pct_flete_nacional_sobre_ventas"] = np.where(r["ventas_total"] > 0,
                                                     (r["flete_nacional"] / r["ventas_total"]).round(4), np.nan)
    r["pct_flete_importacion_sobre_ventas"] = np.where(r["ventas_total"] > 0,
                                                        (r["flete_importacion"] / r["ventas_total"]).round(4), np.nan)
    r["pct_flete_total_sobre_ventas"] = np.where(r["ventas_total"] > 0,
                                                  (r["flete_total"] / r["ventas_total"]).round(4), np.nan)
    # Tendencia últimos 3 vs previos 3
    r["tendencia_flete_pct"] = r["pct_flete_total_sobre_ventas"].rolling(3).mean() - r["pct_flete_total_sobre_ventas"].shift(3).rolling(3).mean()
    _save(r, "fletes_vs_ventas.csv")


# =========================================================
# GRUPO 11: VENTAS POR VENDEDOR
# =========================================================
def g11_ventas_vendedor():
    log.info("[G11] Ventas por Vendedor")
    v = _read("fact_ventas_vendedor.csv")
    if v.empty:
        log.warning("fact_ventas_vendedor vacío, salto G11")
        _save(pd.DataFrame(), "ventas_x_vendedor.csv")
        return
    g = v.groupby(["vendedor", "anio_mes"])["monto_cop"].sum().reset_index()
    tot_mes = g.groupby("anio_mes")["monto_cop"].sum().rename("total_mes").reset_index()
    g = g.merge(tot_mes, on="anio_mes", how="left")
    g["pct_participacion"] = (g["monto_cop"] / g["total_mes"]).round(4)
    g = g.sort_values(["vendedor", "anio_mes"])
    g["crecimiento_pct_mom"] = g.groupby("vendedor")["monto_cop"].pct_change().round(4)
    # Meta prorrateada anual/12 dividida por 5 vendedores
    meta_mes_por_vend = META_ANUAL_2026 / 12 / 5
    g["cumplimiento_meta_prorrata"] = (g["monto_cop"] / meta_mes_por_vend).round(4)
    # Promedio mensual por vendedor
    prom = g.groupby("vendedor")["monto_cop"].mean().round(0).rename("promedio_mensual_vendedor").reset_index()
    g = g.merge(prom, on="vendedor", how="left")
    _save(g, "ventas_x_vendedor.csv")


# =========================================================
# ORQUESTADOR
# =========================================================
def run(fecha_hoy: pd.Timestamp | None = None) -> dict:
    if fecha_hoy is None:
        fecha_hoy = pd.Timestamp.today().normalize()
    log.info("=== CALCULATE METRICS (fecha=%s) ===", fecha_hoy.date())
    results: dict[str, dict] = {}
    for name, fn in [
        ("g1_ventas",              lambda: g1_ventas()),
        ("g2_utilidad_bruta",      lambda: g2_utilidad_bruta()),
        ("g3_rotacion",            lambda: g3_rotacion()),
        ("g4_working_capital",     lambda: g4_working_capital(fecha_hoy)),
        ("g5_dias_cartera",        lambda: g5_dias_cartera(fecha_hoy)),
        ("g6_dias_cxp",            lambda: g6_dias_cxp(fecha_hoy)),
        ("g7_gastos",              lambda: g7_gastos()),
        ("g8_margen_cliente",      lambda: g8_margen_cliente(fecha_hoy)),
        ("g9_margen_producto",     lambda: g9_margen_producto()),
        ("g10_fletes_vs_ventas",   lambda: g10_fletes_vs_ventas()),
        ("g11_ventas_vendedor",    lambda: g11_ventas_vendedor()),
    ]:
        try:
            fn()
            results[name] = {"ok": True}
        except Exception as e:
            log.exception("Falla %s: %s", name, e)
            results[name] = {"ok": False, "error": str(e)}
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
