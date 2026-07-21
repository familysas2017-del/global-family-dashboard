"""
Config central: rutas, IDs Drive, constantes.
Todo lo hard-coded del pipeline vive aquí.
"""
from pathlib import Path

# ---- Rutas ----
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDS_PATH   = PROJECT_ROOT / "credentials_global_family.json"
RAW_DIR      = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR    = PROJECT_ROOT / "data" / "clean"
METRICS_DIR  = PROJECT_ROOT / "data" / "metrics"
OUTPUT_DIR   = PROJECT_ROOT / "output"
LOGS_DIR     = PROJECT_ROOT / "logs"

for _d in (RAW_DIR, CLEAN_DIR, METRICS_DIR, OUTPUT_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---- Google Drive ----
DRIVE_FOLDER_ID = "1VXyXbS10gaXFRolCmcsMfkPuuY6ViBNb"
DRIVE_SCOPES    = ["https://www.googleapis.com/auth/drive.readonly"]

# Nombres esperados. Si el archivo del Drive tiene un nombre distinto, el downloader
# lo detecta por coincidencia parcial (case-insensitive).
EXPECTED_FILES = {
    "ventas_hist":     "Ventas junio2024-abril2025.xlsx",
    "analisis_num":    "Global Family - Análisis Numérico.xlsx",
    "gastos":          "Gastos Global.xlsx",
    "cartera":         "Cartera 20 Julio 2026.xlsx",
    "cxp_nacional":    "Cuentas x Pagar Proveedores Nacionales.xlsx",
    "cxp_internacional": "Cuentas x Pagar Proveedores Int.xlsx",
    "pagos_jeison":    "Pagos Jeison Negocio Distri.xlsx",
}

# ---- Categorización de PRODUCTOS (18 categorías) ----
# Reglas de keywords aplicadas a la descripción del producto en mayúsculas.
# Se evalúan en orden; el primer match gana.
CATEGORIZATION_RULES = [
    ("PAÑALES", ["PAÑAL","PANAL","PAÑALITIN","PAMPERS","HUGGIES","WINNY","BABYSEC","PEQUEÑIN","PEQUENIN","PUFFIES"]),
    ("TOALLITAS HÚMEDAS Y PAÑITOS", ["TOALLITA","TOALLA HUMED","PAÑITO HUMED","PANITO HUMED","PAÑITO","PANITO","WIPE","HUMEDAS","HUMEDA"]),
    ("ESTUCHES Y KITS REGALO", ["ESTUCHE","KIT REGALO","BABY SHOWER","ARRURRU","ARRULLO","OBSEQUIO"]),
    ("BAÑO BEBÉ (BAÑERAS Y BACINES)", ["BANERA","BAÑERA","BACIN","ORINAL","BACINILLA","TINA BEBE"]),
    ("MOBILIARIO INFANTIL", ["CORRAL","CAMPING","COMEDOR ","COMEDOR$","SILLA COMEDOR","SILLA MECED","SILLA ALTA","PRAKTICOMED","CUNA ","COLCHON","COLCHÓN","CAMA INFANT","CAMA NIDO","MOISES","MOISÉS","ESCRITORIO","MESA INFANT","TOCADOR","COLCHONETA"]),
    ("CAMINADORES Y MONTABLES", ["CARRO MONTABLE","CAMINADOR","ANDADOR","ANDADERA","MONTABLE","PASEADOR","CARGADOR BULL","RETRO CAMPIONI","SPEEDY CAMPIONI","TRICICLO","BICICLET","PATIN","PATÍN"]),
    ("COCHES Y PORTEO", ["COCHE BEBE","COCHE BEBÉ","COCHE PRIORI","COCHE ","COCHECITO","CARRIOLA","SILLA CARRO","SILLA AUTO","PORTABEBE","PORTABEBÉ","CANGURO ","CARGADOR AIE","CARGADOR BEBE","CARGADOR BEBÉ","CARGADOR DELTA","CARGADOR ERGO","CARGADOR TIPO"]),
    ("ACCESORIOS BEBÉ", ["REDUCTOR BANO","REDUCTOR BAÑO","TOLDILLO","COJIN LACTANC","COJÍN LACTANC"]),
    ("ALIMENTACIÓN INFANTIL", ["FORMULA","NAN ","NIDO","NESTOGENO","ENFAMIL","SIMILAC","NUTRAMIGEN","SANCOR","PROGRESS","GERBER","COMPOTA","PAPILLA","COLADA","CEREAL INF","CEREALES INF"]),
    ("BIBERONES Y EXTRACTORES", ["BIBERON","TETERO","CHUPO","CHUPETE","PEZONERA","EXTRACTOR LECHE","EXTRACTOR ","SACALECHE","MAMADERA","VASO ENTRENA"]),
    ("CUIDADO DENTAL", ["CEPILLO DENT","CREMA DENT","PASTA DENT","ENJUAGUE BUCAL","HILO DENTAL"]),
    ("CUIDADO FEMENINO Y MATERNIDAD", ["TOALLA HIGIE","TAMPON","PROTECTOR DIARIO","COPA MENSTR","NOSOTRAS","KOTEX","STAYFREE","POSPARTO","MATERNITY","MATERN"]),
    ("HIGIENE PERSONAL", ["SHAMPOO","CHAMPU","JABON","JABÓN","BAÑO","BANO LIQU","GEL DUCHA","GEL BAÑO","GEL BANO","ESPUMA BAÑO","COLONIA","TALCO"]),
    ("CREMAS Y CUIDADO PIEL", ["CREMA","LOCION","LOCIÓN","VASELINA","OLEO","ÓLEO","ACEITE BEBE","ACEITE BEBÉ","HIDRATANTE","PROTECTOR SOLAR","BLOQUEADOR"]),
    ("PAPEL Y SERVILLETAS", ["PAPEL HIGIE","PAPEL HIGI","SERVILLETA","PAÑUELO DESECH","PANUELO DESECH","ROLLO COCINA","TOALLA COCINA"]),
    ("ASEO HOGAR", ["DETERGENTE","JABON ROPA","SUAVIZANTE","BLANQUEADOR","CLORO","LIMPIADOR","DESINFECT","DESENGRAS","AMBIENTADOR","AROMATIZ","INSECTICID","ESCOBA","TRAPEAD","GUANTE COC","ESPONJA"]),
    ("BELLEZA Y CUIDADO PERSONAL", ["MAQUILL","LABIAL","ESMALTE","PESTAÑA","PESTANA","SOMBRA","RIMEL","RUBOR","TINTE","TINTURA","KERATINA","DESODORANTE","AFEITAR","RASURADOR","CUCHILLA"]),
    ("JUGUETES Y ACCESORIOS", ["JUGUETE","SONAJER","PELUCHE","MORDEDOR","MUÑECA","MUNECA","CARRITO","TAPETE","GIMNASIO","MONITOR BEBE","PISCINA BEBE"]),
    ("ROPA Y TEXTIL", ["BODY ","PIJAMA","CAMISETA","PANTALON","MEDIA","GORRITO","BABERO","COBIJA","SABANA","SÁBANA","TOALLA BEBE","TOALLA BEBÉ","MANTA","COBERTOR"]),
    ("ALIMENTOS Y BEBIDAS", ["CHOCOLA","GALLET","DULCE","CARAMELO","CHICLE","BOMBOM","CHUPETA","GASEOSA","BEBIDA","JUGO","AGUA ","LECHE ","YOGUR","AVENA","CHOCLITO","PAPAS ","PAQUETICO","SNACK"]),
    ("FARMACIA Y BOTIQUÍN", ["ACETAMIN","IBUPROF","ALCOHOL","AGUA OXIG","CURITA","BANDITA","VENDAJE","GASA","SUERO","TERMOMET","JERINGA","VITAMINA"]),
]

# ---- Clasificación de GASTOS ----
GASTOS_FIJOS = {
    "Nomina", "Arriendos", "Planilla salud y pensión", "Servicios Públicos",
    "Seguros", "Contabilidad", "Software", "Plan de Datos", "Cuota de Manejo",
    "Cesantias", "Bono Navidad",
}
GASTOS_VARIABLES = {
    "Comisiones a Vendedores", "Viáticos Vendedores", "Viáticos Logística",
    "Viáticos Viajes Armenia", "Fletes Nacionales", "Fletes Locales",
    "Publicidad", "Anuncios en Redes", "Empaques", "Insumos Bodega",
    "Insumos Oficina", "Gasolina", "Gastos Camión SQD932", "Gastos Camión TJB331",
    "Adecuaciones Bodega", "Material Impreso", "Dotación", "Relaciones Públicas",
    "Varios", "Aseo", "Seguridad Privada", "Equipos de Oficina",
    "Comisión Consignaciones CB", "Comisiones Bancarias",
    "Servicio Pago a Proveedores", "Servicio Pago de Nomina", "Servicio Pago a Otros",
    "Descuentos por Act", "Rebate",
}
GASTOS_NO_OPERACIONALES = {
    "Intereses", "Intereses a las cesantias", "4 x mil", "Autorretención",
    "Impuesto Ica", "Industria y Comercio",
}
GASTOS_COSTO_IMPORTACION = {
    "Viajes China", "Viajes Panamá", "Comisiones Swift",
}
# Todo lo demás → OPERACIONAL

# ---- Ventana temporal de análisis (para métricas de "últimos N días") ----
VENTANA_3M_DIAS   = 90
VENTANA_6M_DIAS   = 180
VENTANA_30D_DIAS  = 30
VENTANA_60D_DIAS  = 60
VENTANA_90D_DIAS  = 90

# ---- Fecha de referencia (hoy) para cálculos ----
# Se puede sobreescribir vía CLI para reprocesar históricos.
import datetime
FECHA_HOY = datetime.date.today()

# ---- Meta anual ----
META_ANUAL_2026 = 9_000_000_000  # $9 mil millones COP
