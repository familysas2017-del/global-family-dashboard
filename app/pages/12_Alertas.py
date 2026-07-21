"""Página 12: Centro de Alertas."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import streamlit as st

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters
from utils.formatters import formato_pesos, formato_pct, formato_numero

st.set_page_config(page_title="Alertas · GFD", page_icon="🚨", layout="wide")
st.markdown("<h2 style='color:#1B3A5C'>🚨 Centro de Alertas</h2>", unsafe_allow_html=True)
st.caption("Consolida los semáforos, alertas críticas y buenas noticias del negocio.")

filters = render_sidebar_filters()

# ============================================================
# CRÍTICAS
# ============================================================
st.markdown("### 🔴 Alertas críticas")

criticos_encontrados = False

# 1) Cartera vencida >90
gt90 = get_data("dias_cartera_vencidas_gt90")
if not gt90.empty and "saldo_pendiente" in gt90.columns:
    total_gt90 = gt90["saldo_pendiente"].sum()
    if len(gt90) > 0:
        criticos_encontrados = True
        with st.expander(f"💵 **{len(gt90)} facturas** vencidas >90 días · {formato_pesos(total_gt90, 1)}", expanded=True):
            show = gt90.copy()
            if "fecha_limite_pago" in show.columns:
                show["fecha_limite_pago"] = pd.to_datetime(show["fecha_limite_pago"], errors="coerce").dt.strftime("%Y-%m-%d")
            show = show.sort_values("saldo_pendiente", ascending=False).head(20)
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.markdown("**Acción sugerida:** contactar a los 5 clientes con más saldo y ofrecer plan de pago.")

# 2) Productos MUERTOS con inventario > $10M
esc = get_data("escalera_rotacion_productos")
if not esc.empty:
    muertos_caros = esc[(esc["clasificacion_rotacion"]=="MUERTO") & (esc["costo_total_inventario"]>10_000_000)]
    if len(muertos_caros) > 0:
        criticos_encontrados = True
        total = muertos_caros["costo_total_inventario"].sum()
        with st.expander(f"📦 **{len(muertos_caros)} productos MUERTOS** con inventario > $10M · {formato_pesos(total, 1)}", expanded=False):
            show = muertos_caros.sort_values("costo_total_inventario", ascending=False).head(20)[
                ["descripcion","categoria_producto","stock_actual","costo_total_inventario","dias_sin_venta"]
            ]
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.markdown("**Acción sugerida:** promoción, liquidación o devolución a proveedor.")

# 3) CxP vencidas
cxp_nal = get_data("fact_cxp_nacional")
if not cxp_nal.empty and "tramo_aging" in cxp_nal.columns:
    vencidas = cxp_nal[cxp_nal["tramo_aging"].str.contains("vencida", na=False) & (cxp_nal["saldo_pendiente"]>0)]
    if len(vencidas) > 0:
        criticos_encontrados = True
        total = vencidas["saldo_pendiente"].sum()
        with st.expander(f"🧾 **{len(vencidas)} facturas** a proveedores VENCIDAS · {formato_pesos(total, 1)}", expanded=False):
            show = vencidas.sort_values("saldo_pendiente", ascending=False).head(20)[
                ["proveedor","documento","fecha_vencimiento","saldo_pendiente","dias_vencido","tramo_aging"]
            ]
            show["fecha_vencimiento"] = pd.to_datetime(show["fecha_vencimiento"], errors="coerce").dt.strftime("%Y-%m-%d")
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.markdown("**Acción sugerida:** priorizar pago para evitar cortes de suministro y sobrecostos.")

# 4) Clientes con margen negativo (top perdedores)
mx = get_data("margen_x_cliente")
if not mx.empty:
    neg = mx[(mx["margen_bruto"]<0) & (~mx["generico"].fillna(False))].nsmallest(15, "margen_bruto")
    if len(neg) > 0:
        criticos_encontrados = True
        with st.expander(f"👤 **{len(neg)} clientes** con margen negativo (top 15)", expanded=False):
            show = neg[["cliente","venta_total","margen_bruto","margen_bruto_pct","cantidad_facturas"]].copy()
            for c in ["venta_total","margen_bruto"]:
                show[c] = show[c].map(lambda v: formato_pesos(v, 1))
            show["margen_bruto_pct"] = show["margen_bruto_pct"].map(lambda v: formato_pct(v) if pd.notna(v) else "-")
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.markdown("**Acción sugerida:** revisar precios, descuentos y costo asignado. Puede ser cliente de bajo margen intencional.")

if not criticos_encontrados:
    st.success("✅ Sin alertas críticas.")

st.markdown("---")

# ============================================================
# ADVERTENCIAS
# ============================================================
st.markdown("### 🟡 Advertencias")
adv_encontradas = False

# 1) DORMIDOS con inventario alto
if not esc.empty:
    dormidos_caros = esc[(esc["clasificacion_rotacion"]=="DORMIDO") & (esc["costo_total_inventario"]>5_000_000)]
    if len(dormidos_caros) > 0:
        adv_encontradas = True
        with st.expander(f"😴 **{len(dormidos_caros)} productos DORMIDOS** con inventario > $5M", expanded=False):
            show = dormidos_caros.sort_values("costo_total_inventario", ascending=False).head(15)[
                ["descripcion","categoria_producto","stock_actual","costo_total_inventario","dias_sin_venta"]
            ]
            st.dataframe(show, use_container_width=True, hide_index=True)

# 2) Categorías decrecientes
cat_crec = get_data("categorias_crecimiento")
if not cat_crec.empty and "clasificacion" in cat_crec.columns:
    dec = cat_crec[cat_crec["clasificacion"]=="DECRECIENDO"]
    if len(dec) > 0:
        adv_encontradas = True
        with st.expander(f"📉 **{len(dec)} categorías** en decrecimiento vs trimestre anterior", expanded=False):
            st.dataframe(dec, use_container_width=True, hide_index=True)

# 3) Clientes A o B >45 días sin comprar
if not mx.empty:
    if "clasificacion_abc" in mx.columns and "dias_sin_comprar" in mx.columns:
        inactivos_ab = mx[mx["clasificacion_abc"].isin(["A","B"]) & (mx["dias_sin_comprar"] > 45) & (~mx["generico"].fillna(False))]
        if len(inactivos_ab) > 0:
            adv_encontradas = True
            with st.expander(f"⏰ **{len(inactivos_ab)} clientes A/B** llevan >45 días sin comprar", expanded=False):
                show = inactivos_ab.nsmallest(20, "dias_sin_comprar")[
                    ["cliente","clasificacion_abc","venta_total","dias_sin_comprar","ultima_compra"]
                ].copy()
                show["venta_total"] = show["venta_total"].map(lambda v: formato_pesos(v, 1))
                show["ultima_compra"] = pd.to_datetime(show["ultima_compra"], errors="coerce").dt.strftime("%Y-%m-%d")
                st.dataframe(show, use_container_width=True, hide_index=True)
                st.markdown("**Acción sugerida:** llamada del vendedor asignado para reactivación.")

if not adv_encontradas:
    st.info("No hay advertencias abiertas.")

st.markdown("---")

# ============================================================
# POSITIVAS
# ============================================================
st.markdown("### 🟢 Positivas")
pos_encontradas = False

# 1) Categorías creciendo
if not cat_crec.empty and "clasificacion" in cat_crec.columns:
    crec = cat_crec[cat_crec["clasificacion"]=="CRECIENDO"]
    if len(crec) > 0:
        pos_encontradas = True
        with st.expander(f"📈 **{len(crec)} categorías** en crecimiento", expanded=False):
            st.dataframe(crec, use_container_width=True, hide_index=True)

# 2) Cumplimiento meta on-track
vm = get_data("venta_mensual")
if not vm.empty:
    v2026 = float(vm[vm["anio_mes"].str.startswith("2026")]["venta_neta"].sum())
    meses_transc = int((vm["anio_mes"] >= "2026-01").sum())
    if meses_transc > 0:
        pct_esperado = meses_transc / 12
        pct_real = v2026 / 9_000_000_000
        if pct_real >= pct_esperado * 0.9:
            pos_encontradas = True
            st.success(f"🎯 Meta 2026 **on-track**: llevas **{pct_real*100:.1f}%** vs {pct_esperado*100:.1f}% esperado a esta altura.")

# 3) DSO < DPO
dso = get_data("dias_cartera_resumen")
dpo_res = get_data("dias_cxp_resumen")
if not dso.empty and not dpo_res.empty:
    v_dso = float(dso.iloc[0]["valor"])
    row_glob = dpo_res[dpo_res["tipo"]=="global"]
    v_dpo = float(row_glob.iloc[0]["dpo"]) if len(row_glob) else 0
    if v_dso < v_dpo:
        pos_encontradas = True
        st.success(f"💰 **DSO {v_dso:.0f} d < DPO {v_dpo:.0f} d** → cobras más rápido de lo que pagas (ciclo de caja favorable).")

# 4) Clientes nuevos del último mes
dc = get_data("dim_clientes")
if not dc.empty and "primera_compra" in dc.columns:
    dc["primera_compra"] = pd.to_datetime(dc["primera_compra"], errors="coerce")
    ult_mes = dc["primera_compra"].max().to_period("M") if pd.notna(dc["primera_compra"].max()) else None
    if ult_mes is not None:
        nuevos = dc[dc["primera_compra"].dt.to_period("M") == ult_mes]
        if len(nuevos) > 0:
            pos_encontradas = True
            with st.expander(f"🆕 **{len(nuevos)} clientes nuevos** en el último mes ({ult_mes})", expanded=False):
                show = nuevos[["cliente","primera_compra","total_facturas"]].copy()
                show["primera_compra"] = show["primera_compra"].dt.strftime("%Y-%m-%d")
                st.dataframe(show, use_container_width=True, hide_index=True)

if not pos_encontradas:
    st.info("No hay noticias positivas detectadas en este momento.")
