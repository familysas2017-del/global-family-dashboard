# Global Family Distribuciones - Dashboard Comercial

Dashboard de inteligencia comercial para Global Family Distribuciones.

## Páginas
- Home: Resumen ejecutivo con KPIs principales
- Ventas: Tendencias mensuales, por categoría, drill-down
- Utilidad Bruta: Margen bruto global y por categoría
- Margen por Cliente: Ranking ABC, ticket medio
- Margen por Producto: Rentabilidad por SKU
- Rotación de Inventario: Productos activos, dormidos, muertos
- Working Capital: Capital de trabajo y razón corriente
- Cartera (DSO): Días de cobro, aging
- Cuentas por Pagar (DPO): Días de pago, calendario
- Gastos: Fijos vs variables, operacionales vs no operacionales
- Fletes vs Ventas: Costo logístico como % de ventas
- Ventas por Vendedor: Cumplimiento de meta
- Alertas: Semáforos y acciones sugeridas

## Ejecución local
```bash
cd app
streamlit run Home.py
```

## Actualización de datos
```bash
python pipeline/run_pipeline.py
```
