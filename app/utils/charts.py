"""Funciones reutilizables de gráficos con Plotly. Paleta corporativa unificada."""
from __future__ import annotations
from typing import Sequence

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ---- Paleta ----
COLOR_PRIMARIO   = "#1B3A5C"
COLOR_SECUNDARIO = "#2E86AB"
COLOR_POSITIVO   = "#28A745"
COLOR_NEGATIVO   = "#DC3545"
COLOR_NEUTRO     = "#FFC107"
COLOR_FONDO      = "#F8F9FA"
COLOR_TEXTO      = "#212529"

# Paleta discreta para series múltiples (categorías, etc.)
PALETA_SERIES = [
    "#1B3A5C", "#2E86AB", "#28A745", "#FFC107", "#DC3545",
    "#6F42C1", "#20C997", "#FD7E14",
]

# Escala verde↔rojo (para heatmap divergente)
ESCALA_DIVERGENTE = [
    [0.0, "#DC3545"],
    [0.5, "#FFC107"],
    [1.0, "#28A745"],
]

# Escala secuencial azul (para heatmap positivo)
ESCALA_AZUL = [
    [0.0, "#EDF2F7"],
    [0.5, "#2E86AB"],
    [1.0, "#1B3A5C"],
]


def _base_layout(fig: go.Figure, title: str | None = None, height: int | None = None) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=COLOR_PRIMARIO)) if title else None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=12, color=COLOR_TEXTO),
        margin=dict(l=10, r=10, t=40 if title else 10, b=10),
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(color=COLOR_TEXTO))
    fig.update_yaxes(showgrid=True, gridcolor="#E9ECEF", zeroline=False, tickfont=dict(color=COLOR_TEXTO))
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str | None = None,
              color: str | None = None, color_discrete: str = COLOR_SECUNDARIO,
              orientation: str = "v", height: int = 380,
              text_format: str | None = None) -> go.Figure:
    if df.empty:
        return _base_layout(go.Figure(), title, height)
    fig = px.bar(df, x=x, y=y, color=color, orientation=orientation,
                 color_discrete_sequence=PALETA_SERIES if color else [color_discrete])
    if text_format:
        fig.update_traces(texttemplate=text_format, textposition="outside")
    return _base_layout(fig, title, height)


def horizontal_bar(df: pd.DataFrame, x: str, y: str, title: str | None = None,
                   color_col: str | None = None, height: int = 400,
                   text_format: str | None = None) -> go.Figure:
    if df.empty:
        return _base_layout(go.Figure(), title, height)
    fig = px.bar(df, x=x, y=y, orientation="h",
                 color=color_col,
                 color_discrete_sequence=PALETA_SERIES,
                 color_continuous_scale=[[0, COLOR_NEGATIVO], [0.5, COLOR_NEUTRO], [1, COLOR_POSITIVO]])
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    if text_format:
        fig.update_traces(texttemplate=text_format, textposition="outside")
    return _base_layout(fig, title, height)


def line_chart(df: pd.DataFrame, x: str, y, title: str | None = None,
               color: str | None = None, height: int = 380,
               show_trend: bool = False) -> go.Figure:
    if df.empty:
        return _base_layout(go.Figure(), title, height)
    fig = px.line(df, x=x, y=y, color=color, markers=True,
                  color_discrete_sequence=PALETA_SERIES)
    if show_trend and isinstance(y, str) and len(df) >= 2:
        try:
            import numpy as np
            xs = list(range(len(df)))
            slope, intercept = np.polyfit(xs, df[y].fillna(0).values, 1)
            tend = [slope * i + intercept for i in xs]
            fig.add_scatter(x=df[x], y=tend, mode="lines",
                            line=dict(dash="dash", color=COLOR_NEUTRO, width=2),
                            name="Tendencia")
        except Exception:
            pass
    return _base_layout(fig, title, height)


def bar_line_combo(df: pd.DataFrame, x: str, y_bar, y_line: str,
                   title: str | None = None, height: int = 400,
                   bar_names: list[str] | None = None,
                   stacked: bool = False) -> go.Figure:
    """Barras (una o varias) + línea superpuesta en eje secundario."""
    if df.empty:
        return _base_layout(go.Figure(), title, height)
    fig = go.Figure()
    y_bars = y_bar if isinstance(y_bar, (list, tuple)) else [y_bar]
    names = bar_names or y_bars
    for i, ycol in enumerate(y_bars):
        fig.add_bar(x=df[x], y=df[ycol], name=names[i],
                    marker_color=PALETA_SERIES[i % len(PALETA_SERIES)])
    fig.add_scatter(x=df[x], y=df[y_line], name=y_line, yaxis="y2",
                    mode="lines+markers",
                    line=dict(color=COLOR_NEGATIVO, width=3))
    fig.update_layout(
        barmode="stack" if stacked else "group",
        yaxis=dict(title="Monto"),
        yaxis2=dict(title=y_line, overlaying="y", side="right",
                    showgrid=False, tickformat=".1%"),
    )
    return _base_layout(fig, title, height)


def donut_chart(df: pd.DataFrame, values: str, names: str, title: str | None = None,
                height: int = 380) -> go.Figure:
    if df.empty:
        return _base_layout(go.Figure(), title, height)
    fig = px.pie(df, values=values, names=names, hole=0.55,
                 color_discrete_sequence=PALETA_SERIES)
    fig.update_traces(textinfo="percent+label", textposition="outside")
    fig.update_layout(showlegend=True)
    return _base_layout(fig, title, height)


def heatmap(df: pd.DataFrame, x: str, y: str, z: str, title: str | None = None,
            height: int = 420, escala=ESCALA_AZUL) -> go.Figure:
    if df.empty:
        return _base_layout(go.Figure(), title, height)
    piv = df.pivot_table(index=y, columns=x, values=z, aggfunc="sum", fill_value=0)
    fig = go.Figure(data=go.Heatmap(
        z=piv.values, x=piv.columns.astype(str), y=piv.index.astype(str),
        colorscale=escala, hoverongaps=False,
        hovertemplate=f"{y}: %{{y}}<br>{x}: %{{x}}<br>{z}: %{{z:,.0f}}<extra></extra>",
    ))
    return _base_layout(fig, title, height)


def waterfall_chart(labels: Sequence[str], values: Sequence[float],
                    tipos: Sequence[str] | None = None,
                    title: str | None = None, height: int = 420) -> go.Figure:
    """tipos: lista con 'total','relative','relative',... — igual longitud que labels."""
    if not labels:
        return _base_layout(go.Figure(), title, height)
    if tipos is None:
        tipos = ["relative"] * (len(labels) - 1) + ["total"]
    fig = go.Figure(go.Waterfall(
        x=list(labels), y=list(values), measure=list(tipos),
        connector={"line": {"color": "#ADB5BD"}},
        increasing={"marker": {"color": COLOR_POSITIVO}},
        decreasing={"marker": {"color": COLOR_NEGATIVO}},
        totals={"marker": {"color": COLOR_PRIMARIO}},
        text=[f"${v/1e6:,.0f}M" for v in values],
        textposition="outside",
    ))
    return _base_layout(fig, title, height)


def stacked_horizontal_aging(labels: list[str], montos_por_tramo: dict[str, float],
                             title: str | None = None,
                             height: int = 180) -> go.Figure:
    """Barra apilada horizontal única, útil para mostrar aging de cartera/CxP en un solo trazo."""
    colores = {
        "corriente": COLOR_POSITIVO,
        "al_dia":    COLOR_POSITIVO,
        "1-30":      "#95CE72",
        "vencida_1-30":  "#95CE72",
        "31-60":     COLOR_NEUTRO,
        "vencida_31-60": COLOR_NEUTRO,
        "61-90":     "#FD7E14",
        "vencida_61-90": "#FD7E14",
        ">90":       COLOR_NEGATIVO,
        "vencida_>90":   COLOR_NEGATIVO,
    }
    fig = go.Figure()
    for tramo, monto in montos_por_tramo.items():
        fig.add_bar(
            y=["Total"], x=[monto], name=tramo,
            orientation="h", marker_color=colores.get(tramo, COLOR_SECUNDARIO),
            hovertemplate=f"{tramo}: ${monto:,.0f}<extra></extra>",
        )
    fig.update_layout(barmode="stack", showlegend=True, height=height,
                      margin=dict(l=10, r=10, t=40 if title else 10, b=10))
    fig.update_xaxes(showgrid=False, zeroline=False, tickformat=",")
    fig.update_yaxes(visible=False)
    return _base_layout(fig, title, height)


def scatter_bubble(df: pd.DataFrame, x: str, y: str, size: str, color: str,
                   hover_name: str, title: str | None = None,
                   height: int = 450, size_max: int = 40) -> go.Figure:
    if df.empty:
        return _base_layout(go.Figure(), title, height)
    fig = px.scatter(df, x=x, y=y, size=size, color=color, hover_name=hover_name,
                     color_discrete_sequence=PALETA_SERIES,
                     size_max=size_max)
    fig.update_layout(hovermode="closest")
    return _base_layout(fig, title, height)


def box_por_categoria(df: pd.DataFrame, x: str, y: str, title: str | None = None,
                      height: int = 400) -> go.Figure:
    if df.empty:
        return _base_layout(go.Figure(), title, height)
    fig = px.box(df, x=x, y=y,
                 color_discrete_sequence=[COLOR_SECUNDARIO])
    return _base_layout(fig, title, height)
