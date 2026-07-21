"""
Descarga todos los archivos de la carpeta Drive a data/raw/.
Logea nombre, tamaño y timestamp por archivo. Tolerante a fallas.
"""
import logging
import time
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from config import CREDS_PATH, RAW_DIR, DRIVE_FOLDER_ID, DRIVE_SCOPES, EXPECTED_FILES

log = logging.getLogger(__name__)

GOOGLE_NATIVE_MIME_PREFIX = "application/vnd.google-apps"
EXPORT_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _connect():
    creds = service_account.Credentials.from_service_account_file(
        str(CREDS_PATH), scopes=DRIVE_SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_folder(drive) -> list[dict]:
    resp = drive.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and trashed = false",
        pageSize=500,
        fields="files(id, name, mimeType, size, modifiedTime, md5Checksum)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    return resp.get("files", [])


def _download_one(drive, file_meta: dict, dest: Path) -> int:
    """Descarga o exporta; devuelve bytes escritos."""
    mime = file_meta["mimeType"]
    if mime.startswith(GOOGLE_NATIVE_MIME_PREFIX):
        req = drive.files().export_media(fileId=file_meta["id"], mimeType=EXPORT_XLSX_MIME)
        if not dest.suffix:
            dest = dest.with_suffix(".xlsx")
    else:
        req = drive.files().get_media(fileId=file_meta["id"], supportsAllDrives=True)
    with open(dest, "wb") as fh:
        dl = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
    return dest.stat().st_size


def run() -> dict:
    """Descarga los 7 archivos. Devuelve resumen {alias: {path, size, ok, error}}."""
    log.info("=== DOWNLOAD DRIVE ===")
    t0 = time.time()
    drive = _connect()
    files = list_folder(drive)
    log.info("Archivos en carpeta Drive: %d", len(files))

    # Index por nombre lower-case para búsqueda flexible
    files_by_lc = {f["name"].lower(): f for f in files}
    used_ids: set[str] = set()

    # Anclas específicas por alias (palabras distintivas que deben aparecer)
    ANCHORS = {
        "ventas_hist":       ["ventas", "junio2024"],
        "analisis_num":      ["analisis", "num"],   # sin tildes al comparar
        "gastos":            ["gastos", "global"],
        "cartera":           ["cartera"],
        "cxp_nacional":      ["cuentas", "pagar", "nacional"],
        "cxp_internacional": ["cuentas", "pagar", "int"],
        "pagos_jeison":      ["pagos", "jeison"],
    }

    def _norm(s: str) -> str:
        import unicodedata
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return s.lower()

    summary: dict[str, dict] = {}
    for alias, expected_name in EXPECTED_FILES.items():
        entry = {"path": None, "size": 0, "ok": False, "error": None,
                 "expected_name": expected_name, "found_name": None}
        # Match exacto primero
        found = files_by_lc.get(expected_name.lower())
        if found and found["id"] in used_ids:
            found = None
        if not found:
            # Match por TODAS las anclas (todas deben estar en el nombre)
            anchors = [_norm(a) for a in ANCHORS.get(alias, [_norm(expected_name).split()[0]])]
            candidates = [
                m for name_lc, m in files_by_lc.items()
                if m["id"] not in used_ids and all(a in _norm(name_lc) for a in anchors)
            ]
            # excluir CxP nacional cuando buscamos internacional y viceversa
            if alias == "cxp_internacional":
                candidates = [c for c in candidates if "nacional" not in _norm(c["name"])]
            if alias == "cxp_nacional":
                candidates = [c for c in candidates if "int.xlsx" not in _norm(c["name"]) and "internacional" not in _norm(c["name"])]
            if candidates:
                found = candidates[0]
        if not found:
            entry["error"] = f"No encontrado en Drive (esperado: {expected_name})"
            log.warning("  [MISS] %s", expected_name)
            summary[alias] = entry
            continue

        entry["found_name"] = found["name"]
        used_ids.add(found["id"])
        dest = RAW_DIR / found["name"]
        try:
            size = _download_one(drive, found, dest)
            entry.update(path=str(dest), size=size, ok=True)
            log.info("  [OK]  %12s B  %s", f"{size:,}", found["name"])
        except Exception as e:
            entry["error"] = str(e)
            log.exception("  [FAIL] %s : %s", found["name"], e)
        summary[alias] = entry

    log.info("Descarga completada en %.1fs. %d/%d OK.",
             time.time() - t0,
             sum(1 for s in summary.values() if s["ok"]),
             len(summary))
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
