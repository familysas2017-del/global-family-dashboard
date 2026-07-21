"""Página 8: Gestión de Cuentas por Pagar."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import plotly.express as px

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters
from utils.formatters import formato_pesos, formato_dias, formato_numero, formato_pct
from utils.kpi_cards import kpi_row
from utils.charts import (
    stacked_horizontal_aging, PALETA_SERIES,
    COLOR_PRIMARIO, COLOR_POSITIVO, COLOR_NEGATIVO, COLOR_NEUTRO,
)

st.set_page_config(page_title="Cuentas por Pagar · GFD", page_icon="🧾", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>🧾 Gestión de Cuentas por Pagar</h2>", unsafe_allow_html=True)

filters = render_sidebar_filters()

cxp_nal = get_data("fact_cxp_nacional")
cxp_int = get_data("fact_cxp_internacional")
dpo_res = get_data("dias_cxp_resumen")
aging_nal = get_data("dias_cxp_aging_nacional")
prox = get_data("dias_cxp_proximos_vencimientos")

# ===== KPIs =====
saldo_nal = float(cxp_nal["saldo_pendiente"].sum()) if not cxp_nal.empty else 0
saldo_int_cop = float(cxp_int["saldo_pendiente_cop"].sum()) if not cxp_int.empty else 0
saldo_int_usd = float(cxp_int["saldo_pendiente_usd"].sum()) if not cxp_int.empty and "saldo_pendiente_usd" in cxp_int.columns else 0
saldo_total = saldo_nal + saldo_int_cop
if not dpo_res.empty:
    row_global = dpo_res[dpo_res["tipo"]=="global"]
    dpo = float(row_global.iloc[0]["dpo"]) if len(row_global) else 0
else:
    dpo = 0

kpi_row([
    {"label": "CxP Total (Nal+Int)", "value": formato_pesos(saldo_total, 1)},
    {"label": "DPO",                  "value": formato_dias(dpo)},
    {"label": "CxP Nacional",         "value": formato_pesos(saldo_nal, 1)},
    {"label": "CxP Internacional",
     "value": formato_pesos(saldo_int_cop, 1),
     "delta": f"US${saldo_int_usd:,.0f}",
     "delta_color": "off"},
])

st.markdown("---")

# ===== Aging CxP Nacional =====
c1, c2 = st.columns([2, 1])
with c1:
    st.subheader("Aging CxP Nacional")
    if not aging_nal.empty:
        # Ordenar tramos como en la métrica
        tramos_orden = ["al_dia","vencida_1-30","vencida_31-60","vencida_61-90","vencida_>90"]
        aging_nal_ord = aging_nal.set_index("tramo_aging").reindex(tramos_orden).fillna(0).reset_index()
        aging_nal_ord = aging_nal_ord[aging_nal_ord["tramo_aging"].notna()]
        # No pintar la fila 'pagada' aunque venga
        aging_nal_ord = aging_nal_ord[~aging_nal_ord["tramo_aging"].isin(["pagada"])]
        montos = dict(zip(aging_nal_ord["tramo_aging"], aging_nal_ord["monto"].astype(float)))
        fig = stacked_horizontal_aging(list(montos.keys()), montos, height=200)
        st.plotly_chart(fig, use_container_width=True)
        show = pd.DataFrame({
            "Tramo": aging_nal_ord["tramo_aging"],
            "Monto": aging_nal_ord["monto"].map(lambda v: formato_pesos(v, 1)),
            "Nº fact.": aging_nal_ord["n"].map(formato_numero),
            "% total": aging_nal_ord["pct_total"].map(lambda v: f"{v*100:.1f}%"),
        })
        st.dataframe(show, use_container_width=True, hide_index=True)

with c2:
    st.subheader("Composición Nal vs Int")
    df_ni = pd.DataFrame({"tipo":["Nacional","Internacional"],
                          "saldo":[saldo_nal, saldo_int_cop]})
    fig = px.pie(df_ni, values="saldo", names="tipo", hole=0.55,
                 color_discrete_sequence=[COLOR_PRIMARIO, COLOR_NEUTRO])
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=280, margin=dict(l=10, r=10, t=10, b=10),
                      showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Top 10 proveedores por saldo =====
st.subheader("Top 10 proveedores por saldo pendiente")

frames = []
if not cxp_nal.empty:
    a = cxp_nal.groupby("proveedor").agg(saldo=("saldo_pendiente","sum"),
                                          n=("saldo_pendiente","count")).reset_index()
    a["tipo"] = "Nacional"
    frames.append(a)
if not cxp_int.empty:
    b = cxp_int.groupby("proveedor").agg(saldo=("saldo_pendiente_cop","sum"),
                                          n=("saldo_pendiente_cop","count")).reset_index()
    b["tipo"] = "Internacional"
    frames.append(b)

if frames:
    prov = pd.concat(frames, ignore_index=True)
    prov = prov[prov["saldo"] > 0].sort_values("saldo", ascending=False).head(10)
    # Próximo vencimiento
    proximos_map = {}
    if not prox.empty and "proveedor" in prox.columns:
        proximos_map = prox.groupby("proveedor")["fecha_vencimiento"].min().to_dict()
    prov["prox_venc"] = prov["proveedor"].map(
        lambda p: proximos_map.get(p, "s/f")
    )
    show = pd.DataFrame({
        "Proveedor": prov["proveedor"],
        "Tipo": prov["tipo"],
        "Saldo": prov["saldo"].map(lambda v: formato_pesos(v, 1)),
        "Nº fact.": prov["n"].map(formato_numero),
        "Próx. venc.": prov["prox_venc"].apply(
            lambda v: pd.to_datetime(v).strftime("%Y-%m-%d") if pd.notna(v) and v != "s/f" else "-"),
    })
    st.dataframe(show, use_container_width=True, hide_index=True)

st.markdown("---")

# ===== Calendario de pagos =====
st.subheader("Calendario de próximos vencimientos")
if not prox.empty:
    hoy = pd.Timestamp.today().normalize()
    prox2 = prox.copy()
    prox2["fecha_vencimiento"] = pd.to_datetime(prox2["fecha_vencimiento"], errors="coerce")
    valor_col = "saldo_pendiente" if "saldo_pendiente" in prox2.columns else "monto"

    def _tramo_venc(f):
        if pd.isna(f):
            return "sin_fecha"
        d = (f - hoy).days
        if d < 0: return "vencido"
        if d <= 7: return "esta_semana"
        if d <= 14: return "prox_2_sem"
        if d <= 30: return "prox_mes"
        return "mas_1_mes"

    prox2["_bucket"] = prox2["fecha_vencimiento"].map(_tramo_venc)
    orden = ["vencido","esta_semana","prox_2_sem","prox_mes","mas_1_mes"]
    labels = {"vencido":"🔴 Vencido","esta_semana":"🟠 Esta semana",
              "prox_2_sem":"🟡 Próx. 2 semanas","prox_mes":"🟢 Próx. mes","mas_1_mes":"⚪ >1 mes"}
    agg = prox2.groupby("_bucket").agg(total=(valor_col, "sum"), n=(valor_col, "count")).reset_index()
    agg = agg.set_index("_bucket").reindex(orden).fillna(0).reset_index()
    cols = st.columns(len(orden))
    for i, b in enumerate(orden):
        row = agg[agg["_bucket"] == b].iloc[0]
        with cols[i]:
            st.metric(labels[b], formato_pesos(row["total"], 1),
                      delta=f"{int(row['n'])} facturas", delta_color="off")

    # Listado de próximos 30 días
    st.markdown("**Detalle: vencimientos próximos 30 días**")
    prox_30 = prox2[prox2["_bucket"].isin(["vencido","esta_semana","prox_2_sem","prox_mes"])]
    prox_30 = prox_30.sort_values("fecha_vencimiento")
    if not prox_30.empty:
        cols_show = [c for c in ["proveedor","documento","valor_total","saldo_pendiente","fecha_vencimiento","tipo"] if c in prox_30.columns]
        st.dataframe(prox_30[cols_show], use_container_width=True, hide_index=True, height=340)

st.markdown("---")

# ===== CxP Internacional detalle =====
if not cxp_int.empty:
    st.subheader("Detalle CxP Internacional")
    cols_show = [c for c in ["proveedor","documento","fecha_factura","valor_usd","trm","valor_en_sistema",
                             "total_abonado_pesos","saldo_pendiente_usd","saldo_pendiente_cop"]
                 if c in cxp_int.columns]
    show = cxp_int[cols_show].copy()
    for cnum in ["valor_en_sistema","total_abonado_pesos","saldo_pendiente_cop"]:
        if cnum in show.columns:
            show[cnum] = show[cnum].map(lambda v: formato_pesos(v, 1))
    if "valor_usd" in show.columns:
        show["valor_usd"] = show["valor_usd"].map(lambda v: f"US${v:,.0f}" if pd.notna(v) else "-")
    if "saldo_pendiente_usd" in show.columns:
        show["saldo_pendiente_usd"] = show["saldo_pendiente_usd"].map(lambda v: f"US${v:,.0f}" if pd.notna(v) else "-")
    st.dataframe(show, use_container_width=True, hide_index=True)
