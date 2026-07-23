"""
Análisis Global Family Distribuciones
Genera: Analisis_Global_Family_Mayo2026.xlsx
"""
import pandas as pd
import numpy as np
import re
import unicodedata
import warnings
from datetime import timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, FormulaRule
from openpyxl.utils import get_column_letter
from itertools import combinations
from collections import Counter

warnings.filterwarnings('ignore')

SRC = 'Venta Global Family al 21 mayo 2026.xlsx'
OUT = 'Analisis_Global_Family_Mayo2026.xlsx'

# =========================================================
# 1. CARGA Y LIMPIEZA
# =========================================================
print('Leyendo archivo...')
df = pd.read_excel(SRC, sheet_name='Venta')

# Limpieza encoding (caracteres mal codificados)
def fix_str(s):
    if pd.isna(s) or not isinstance(s, str):
        return s
    return (s.replace('�', 'ó')  # genérico, ajustaremos comunes
             .replace('Crédito', 'Crédito')
             .replace('Cr�dito', 'Crédito')
             .replace('Remisi�n', 'Remisión')
             .replace('Electr�nica', 'Electrónica'))

# Mejor: hacer reemplazos específicos por columna
def clean_text(s):
    if pd.isna(s) or not isinstance(s, str):
        return s
    s = s.replace('�', 'ó')
    return s.strip().upper()

def clean_text_keepcase(s):
    if pd.isna(s) or not isinstance(s, str):
        return s
    return s.replace('�', 'ó').strip()

# Normalizar campos de texto
for col in ['Tipo Fact.', 'Forma de Pago', 'Documento']:
    df[col] = df[col].astype(str).str.replace('�', 'é', regex=False).str.strip()
    df.loc[df[col].isin(['nan', 'NaN', '']), col] = np.nan
# fixes específicos
df['Tipo Fact.'] = df['Tipo Fact.'].replace({'Créditodito': 'Crédito'})
df['Documento'] = df['Documento'].replace({'Remisiéon': 'Remisión', 'Electréonica': 'Electrónica'})

# Reemplazo correcto: el � estaba en posición distinta
df['Tipo Fact.'] = df['Tipo Fact.'].str.replace('Cr�dito', 'Crédito', regex=False)
df['Documento'] = df['Documento'].str.replace('Remisi�n', 'Remisión', regex=False)
df['Documento'] = df['Documento'].str.replace('Electr�nica', 'Electrónica', regex=False)

# Cliente, Producto, Categoria: trim y normalizar mayúsculas
df['Cliente'] = df['Cliente'].astype(str).str.strip().str.upper()
df['Cliente'] = df['Cliente'].str.replace(r'\s+', ' ', regex=True)
df['Descripcion Producto'] = df['Descripcion Producto'].astype(str).str.strip().str.upper()
df['Descripcion Producto'] = df['Descripcion Producto'].str.replace(r'\s+', ' ', regex=True)
df['Categoria'] = df['Categoria'].astype(str).str.strip().str.upper()

# Eliminar filas con Total <=0 o cantidad <=0 (anuladas)
n_initial = len(df)
df_clean = df[(df['Total'] > 0) & (df['Cantidad'] > 0)].copy()
n_removed = n_initial - len(df_clean)
print(f'Filas iniciales: {n_initial}, removidas (Total<=0 o Cant<=0): {n_removed}, finales: {len(df_clean)}')

df_clean['Fecha'] = pd.to_datetime(df_clean['Fecha Factura'])
df_clean['Año'] = df_clean['Fecha'].dt.year
df_clean['Mes'] = df_clean['Fecha'].dt.month
df_clean['AñoMes'] = df_clean['Fecha'].dt.to_period('M').astype(str)
df_clean['DiaSemana'] = df_clean['Fecha'].dt.day_name()
df_clean['FechaSolo'] = df_clean['Fecha'].dt.date

# Renombrar provedor para claridad
df_clean = df_clean.rename(columns={'Categoria': 'Proveedor'})

# =========================================================
# 2. CATEGORIZACIÓN DE PRODUCTOS (por keywords en descripción)
# =========================================================
def categorize(desc):
    if pd.isna(desc):
        return 'OTROS'
    d = desc.upper()
    # Pañales (revisar primero por especificidad)
    if any(k in d for k in ['PAÑAL', 'PANAL', 'PAÑALITIN', 'PAMPERS', 'HUGGIES', 'WINNY', 'BABYSEC', 'PEQUEÑIN', 'PEQUENIN', 'PUFFIES']):
        return 'PAÑALES'
    # Toallitas húmedas y pañitos
    if any(k in d for k in ['TOALLITA', 'TOALLA HUMED', 'PAÑITO HUMED', 'PANITO HUMED', 'PAÑITO', 'PANITO', 'WIPE', 'HUMEDAS', 'HUMEDA']):
        return 'TOALLITAS HÚMEDAS Y PAÑITOS'
    # Estuches y kits regalo (arrurru, baby shower, etc.)
    if any(k in d for k in ['ESTUCHE', 'KIT REGALO', 'BABY SHOWER', 'ARRURRU', 'ARRULLO', 'OBSEQUIO']):
        return 'ESTUCHES Y KITS REGALO'
    # Bañeras, bacinillas, soporte baño bebé
    if any(k in d for k in ['BANERA', 'BAÑERA', 'BACIN', 'ORINAL', 'BACINILLA', 'TINA BEBE']):
        return 'BAÑO BEBÉ (BAÑERAS Y BACINES)'
    # Mobiliario infantil
    if any(k in d for k in ['CORRAL', 'CAMPING', 'COMEDOR ', 'COMEDOR$', 'SILLA COMEDOR', 'SILLA MECED', 'SILLA ALTA', 'PRAKTICOMED', 'CUNA ', 'COLCHON', 'COLCHÓN', 'CAMA INFANT', 'CAMA NIDO', 'MOISES', 'MOISÉS', 'ESCRITORIO', 'MESA INFANT', 'TOCADOR', 'COLCHONETA']):
        return 'MOBILIARIO INFANTIL'
    # Caminadores, montables, andadores
    if any(k in d for k in ['CARRO MONTABLE', 'CAMINADOR', 'ANDADOR', 'ANDADERA', 'MONTABLE', 'PASEADOR', 'CARGADOR BULL', 'RETRO CAMPIONI', 'SPEEDY CAMPIONI', 'TRICICLO', 'BICICLET', 'PATIN', 'PATÍN']):
        return 'CAMINADORES Y MONTABLES'
    # Coches / cochecitos / sillas auto / porteo
    if any(k in d for k in ['COCHE BEBE', 'COCHE BEBÉ', 'COCHE PRIORI', 'COCHE ', 'COCHECITO', 'CARRIOLA', 'SILLA CARRO', 'SILLA AUTO', 'PORTABEBE', 'PORTABEBÉ', 'CANGURO ', 'CARGADOR AIE', 'CARGADOR BEBE', 'CARGADOR BEBÉ', 'CARGADOR DELTA', 'CARGADOR ERGO', 'CARGADOR TIPO']):
        return 'COCHES Y PORTEO'
    # Accesorios baño bebé adicionales (reductor, toldillo)
    if any(k in d for k in ['REDUCTOR BANO', 'REDUCTOR BAÑO', 'TOLDILLO', 'COJIN LACTANC', 'COJÍN LACTANC']):
        return 'ACCESORIOS BEBÉ'
    # Fórmulas y alimentación infantil
    if any(k in d for k in ['FORMULA', 'NAN ', 'NIDO', 'NESTOGENO', 'ENFAMIL', 'SIMILAC', 'NUTRAMIGEN', 'SANCOR', 'PROGRESS', 'GERBER', 'COMPOTA', 'PAPILLA', 'COLADA', 'CEREAL INF', 'CEREALES INF']):
        return 'ALIMENTACIÓN INFANTIL'
    # Biberones, chupos, extractores leche
    if any(k in d for k in ['BIBERON', 'TETERO', 'CHUPO', 'CHUPETE', 'PEZONERA', 'EXTRACTOR LECHE', 'EXTRACTOR ', 'SACALECHE', 'MAMADERA', 'VASO ENTRENA']):
        return 'BIBERONES Y EXTRACTORES'
    # Pañitos higiénicos / cuidado dental
    if any(k in d for k in ['CEPILLO DENT', 'CREMA DENT', 'PASTA DENT', 'ENJUAGUE BUCAL', 'HILO DENTAL']):
        return 'CUIDADO DENTAL'
    # Cuidado femenino y postparto
    if any(k in d for k in ['TOALLA HIGIE', 'TAMPON', 'PROTECTOR DIARIO', 'COPA MENSTR', 'NOSOTRAS', 'KOTEX', 'STAYFREE', 'POSPARTO', 'MATERNITY', 'MATERN']):
        return 'CUIDADO FEMENINO Y MATERNIDAD'
    # Higiene corporal (shampoo, jabón)
    if any(k in d for k in ['SHAMPOO', 'CHAMPU', 'JABON', 'JABÓN', 'BAÑO', 'BANO LIQU', 'GEL DUCHA', 'GEL BAÑO', 'GEL BANO', 'ESPUMA BAÑO', 'COLONIA', 'TALCO']):
        return 'HIGIENE PERSONAL'
    # Cremas y cuidado piel
    if any(k in d for k in ['CREMA', 'LOCION', 'LOCIÓN', 'VASELINA', 'OLEO', 'ÓLEO', 'ACEITE BEBE', 'ACEITE BEBÉ', 'HIDRATANTE', 'PROTECTOR SOLAR', 'BLOQUEADOR']):
        return 'CREMAS Y CUIDADO PIEL'
    # Papel higiénico y servilletas
    if any(k in d for k in ['PAPEL HIGIE', 'PAPEL HIGI', 'SERVILLETA', 'PAÑUELO DESECH', 'PANUELO DESECH', 'ROLLO COCINA', 'TOALLA COCINA']):
        return 'PAPEL Y SERVILLETAS'
    # Hogar / aseo
    if any(k in d for k in ['DETERGENTE', 'JABON ROPA', 'SUAVIZANTE', 'BLANQUEADOR', 'CLORO', 'LIMPIADOR', 'DESINFECT', 'DESENGRAS', 'AMBIENTADOR', 'AROMATIZ', 'INSECTICID', 'ESCOBA', 'TRAPEAD', 'GUANTE COC', 'ESPONJA']):
        return 'ASEO HOGAR'
    # Belleza adulto
    if any(k in d for k in ['MAQUILL', 'LABIAL', 'ESMALTE', 'PESTAÑA', 'PESTANA', 'SOMBRA', 'RIMEL', 'RUBOR', 'TINTE', 'TINTURA', 'KERATINA', 'DESODORANTE', 'AFEITAR', 'RASURADOR', 'CUCHILLA']):
        return 'BELLEZA Y CUIDADO PERSONAL'
    # Juguetes / accesorios bebé (incluye tapetes, sonajeros, etc.)
    if any(k in d for k in ['JUGUETE', 'SONAJER', 'PELUCHE', 'MORDEDOR', 'MUÑECA', 'MUNECA', 'CARRITO', 'TAPETE', 'GIMNASIO', 'MONITOR BEBE', 'PISCINA BEBE']):
        return 'JUGUETES Y ACCESORIOS'
    # Ropa / textil bebé
    if any(k in d for k in ['BODY ', 'PIJAMA', 'CAMISETA', 'PANTALON', 'MEDIA', 'GORRITO', 'BABERO', 'COBIJA', 'SABANA', 'SÁBANA', 'TOALLA BEBE', 'TOALLA BEBÉ', 'MANTA', 'COBERTOR']):
        return 'ROPA Y TEXTIL'
    # Snacks / alimentos generales
    if any(k in d for k in ['CHOCOLA', 'GALLET', 'DULCE', 'CARAMELO', 'CHICLE', 'BOMBOM', 'CHUPETA', 'GASEOSA', 'BEBIDA', 'JUGO', 'AGUA ', 'LECHE ', 'YOGUR', 'AVENA', 'CHOCLITO', 'PAPAS ', 'PAQUETICO', 'SNACK']):
        return 'ALIMENTOS Y BEBIDAS'
    # Medicamentos / farmacia
    if any(k in d for k in ['ACETAMIN', 'IBUPROF', 'ALCOHOL', 'AGUA OXIG', 'CURITA', 'BANDITA', 'VENDAJE', 'GASA', 'SUERO', 'TERMOMET', 'JERINGA', 'VITAMINA']):
        return 'FARMACIA Y BOTIQUÍN'
    return 'OTROS'

# Aplicar categorización
products_unique = df_clean[['Cod Interno', 'Descripcion Producto']].drop_duplicates()
products_unique['CategoriaProducto'] = products_unique['Descripcion Producto'].apply(categorize)
cat_map = dict(zip(products_unique['Cod Interno'], products_unique['CategoriaProducto']))
df_clean['CategoriaProducto'] = df_clean['Cod Interno'].map(cat_map)

print('Distribución por categoría:')
print(df_clean.groupby('CategoriaProducto')['Total'].sum().sort_values(ascending=False))

# =========================================================
# 3. IDENTIFICAR CLIENTES OCASIONALES / CONSUMIDOR FINAL
# =========================================================
def is_generic_client(name):
    if pd.isna(name):
        return True
    keywords = ['CONSUMIDOR FINAL', 'CLIENTE OCASIONAL', 'CLIENTE GENERAL',
                'VENTA MOSTRADOR', 'PUBLICO GENERAL', 'PÚBLICO GENERAL',
                'VARIOS', 'CONTADO GENERAL', 'CLIENTE CONTADO']
    n = str(name).upper().strip()
    return any(k in n for k in keywords)

df_clean['ClienteGenerico'] = df_clean['Cliente'].apply(is_generic_client)
print(f"\nClientes genéricos detectados: {df_clean[df_clean['ClienteGenerico']]['Cliente'].nunique()}")
print(df_clean[df_clean['ClienteGenerico']]['Cliente'].unique()[:10])

# Guardar dataframe limpio para uso en sheets
df_clean.to_pickle('df_clean.pkl')
products_unique.to_pickle('products_unique.pkl')
print('\nDatos guardados en df_clean.pkl')
print(f'Total registros limpios: {len(df_clean)}')
print(f'Total facturación: ${df_clean["Total"].sum():,.0f}')
print(f'Total facturas únicas: {df_clean["Factura"].nunique()}')
