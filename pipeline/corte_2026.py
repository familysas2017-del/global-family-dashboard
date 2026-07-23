"""
Corte de datos al 2026: elimina histórico 2024-2025 de los CSVs limpios.
Sobrescribe data/clean/*.csv y reporta filas eliminadas.
"""
from __future__ import annotations
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pandas as pd
from pathlib import Path
from datetime import date

CLEAN = Path("data/clean")
CORTE = "2026-01"           # incluye 2026-01-01 en adelante
CORTE_DATE = pd.Timestamp("2026-01-01")

def _filtrar_por_fecha(df: pd.DataFrame, col_fecha: str) -> tuple[pd.DataFrame, int, int]:
    if col_fecha not in df.columns:
        return df, 0, len(df)
    df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")
    n_pre = len(df)
    df_out = df[df[col_fecha] >= CORTE_DATE].copy()
    return df_out, n_pre - len(df_out), len(df_out)

def _filtrar_por_anio_mes(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int, int]:
    n_pre = len(df)
    df_out = df[df[col].astype(str) >= CORTE].copy()
    return df_out, n_pre - len(df_out), len(df_out)

def _save(df: pd.DataFrame, name: str, n_del: int, n_pre: int):
    df.to_csv(CLEAN / name, index=False, encoding="utf-8")
    print(f"  {name:38s} | eliminadas {n_del:>7,} | quedan {len(df):>7,} | de {n_pre:>7,}")

print("="*95)
print("CORTE 2026 EN data/clean/")
print("="*95)

# ---------- 1. fact_ventas.csv ----------
fv = pd.read_csv(CLEAN / "fact_ventas.csv", low_memory=False)
n_pre = len(fv)
fv, ndel, _ = _filtrar_por_fecha(fv, "fecha")
_save(fv, "fact_ventas.csv", ndel, n_pre)

# ---------- 2. fact_cartera.csv → mantener ----------
c = pd.read_csv(CLEAN / "fact_cartera.csv", low_memory=False)
print(f"  {'fact_cartera.csv':38s} | MANTENIDO      | quedan {len(c):>7,} filas (cartera vigente)")

# ---------- 3. fact_cxp_nacional.csv ----------
cn = pd.read_csv(CLEAN / "fact_cxp_nacional.csv", low_memory=False)
n_pre = len(cn)
# Actividad en 2026 = fecha_factura ≥ 2026 O saldo pendiente > 0 (aún vigente)
cn["fecha_factura"] = pd.to_datetime(cn["fecha_factura"], errors="coerce")
cn["saldo_pendiente"] = pd.to_numeric(cn["saldo_pendiente"], errors="coerce").fillna(0)
mask = (cn["fecha_factura"] >= CORTE_DATE) | (cn["saldo_pendiente"] > 0)
cn = cn[mask].copy()
_save(cn, "fact_cxp_nacional.csv", n_pre - len(cn), n_pre)

# ---------- 4. fact_cxp_internacional.csv ----------
ci = pd.read_csv(CLEAN / "fact_cxp_internacional.csv", low_memory=False)
n_pre = len(ci)
ci["fecha_factura"] = pd.to_datetime(ci["fecha_factura"], errors="coerce")
ci["saldo_pendiente_cop"] = pd.to_numeric(ci["saldo_pendiente_cop"], errors="coerce").fillna(0)
mask = (ci["fecha_factura"] >= CORTE_DATE) | (ci["saldo_pendiente_cop"] > 0) | ci["fecha_factura"].isna()
ci = ci[mask].copy()
_save(ci, "fact_cxp_internacional.csv", n_pre - len(ci), n_pre)

# ---------- 5. fact_gastos.csv ----------
fg = pd.read_csv(CLEAN / "fact_gastos.csv", low_memory=False)
n_pre = len(fg)
fg, ndel, _ = _filtrar_por_fecha(fg, "fecha")
_save(fg, "fact_gastos.csv", ndel, n_pre)

# ---------- 6. fact_ventas_vendedor.csv ----------
fvv = pd.read_csv(CLEAN / "fact_ventas_vendedor.csv", low_memory=False)
n_pre = len(fvv)
fvv, ndel, _ = _filtrar_por_anio_mes(fvv, "anio_mes")
_save(fvv, "fact_ventas_vendedor.csv", ndel, n_pre)

# ---------- 7. fact_deuda_jeison.csv → mantener ----------
dj = pd.read_csv(CLEAN / "fact_deuda_jeison.csv", low_memory=False)
print(f"  {'fact_deuda_jeison.csv':38s} | MANTENIDO      | quedan {len(dj):>7,} (cuotas)")

# ---------- 8. dim_inventario.csv → mantener ----------
inv = pd.read_csv(CLEAN / "dim_inventario.csv", low_memory=False)
print(f"  {'dim_inventario.csv':38s} | MANTENIDO      | quedan {len(inv):>7,} (snapshot)")

# ---------- 9. dim_clientes.csv → regenerar con clientes 2026 ----------
clientes_2026 = fv["ident_cliente"].dropna().unique()
dc = pd.read_csv(CLEAN / "dim_clientes.csv", low_memory=False)
n_pre = len(dc)
dc_id_col = "id_cliente" if "id_cliente" in dc.columns else "ident_cliente"
dc = dc[dc[dc_id_col].isin(clientes_2026)].copy()
_save(dc, "dim_clientes.csv", n_pre - len(dc), n_pre)

# ---------- 10. dim_productos.csv → regenerar con productos 2026 ----------
prods_2026 = fv["cod_interno"].dropna().unique()
dp = pd.read_csv(CLEAN / "dim_productos.csv", low_memory=False)
n_pre = len(dp)
dp = dp[dp["cod_interno"].isin(prods_2026)].copy()
_save(dp, "dim_productos.csv", n_pre - len(dp), n_pre)

# ---------- 11. dim_proveedores.csv → mantener ----------
dpr = pd.read_csv(CLEAN / "dim_proveedores.csv", low_memory=False)
print(f"  {'dim_proveedores.csv':38s} | MANTENIDO      | quedan {len(dpr):>7,}")

# ---------- 12. dim_calendario.csv → solo 2026 ----------
dcal = pd.read_csv(CLEAN / "dim_calendario.csv", low_memory=False)
n_pre = len(dcal)
dcal, ndel, _ = _filtrar_por_fecha(dcal, "fecha")
_save(dcal, "dim_calendario.csv", ndel, n_pre)

# ---------- 13. costo_ventas_er.csv → solo 2026 ----------
cer = pd.read_csv(CLEAN / "costo_ventas_er.csv", low_memory=False)
n_pre = len(cer)
cer, ndel, _ = _filtrar_por_anio_mes(cer, "anio_mes")
_save(cer, "costo_ventas_er.csv", ndel, n_pre)

# ---------- Reporte final ----------
print("\n" + "="*95)
print("TOTALES DE CONTROL 2026 (solo datos que quedaron):")
print("="*95)
print(f"  Ventas Netas (fact_ventas):   ${fv['venta_neta_linea'].sum():>18,.0f}")
print(f"  Utilidad Bruta:               ${fv['margen_bruto_linea'].sum():>18,.0f}")
print(f"  Margen bruto:                 {fv['margen_bruto_linea'].sum()/fv['venta_neta_linea'].sum()*100:.2f}%")
print(f"  Facturas únicas 2026:         {fv['factura'].nunique():>18,}")
print(f"  Cartera pendiente:            ${c['saldo_pendiente'].sum():>18,.0f}")
print(f"  CxP Nal pendiente:            ${cn['saldo_pendiente'].sum():>18,.0f}")
print(f"  CxP Int pendiente:            ${ci['saldo_pendiente_cop'].sum():>18,.0f}")
print(f"  Inventario:                   ${inv['costo_total_inventario'].sum():>18,.0f}")
print(f"  Gastos 2026:                  ${fg['valor_cop'].sum():>18,.0f}")
