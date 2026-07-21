"""
Orquestador: download → normalize → build_model → calculate_metrics.
Logging por paso con duración; tolerante a fallas.

Uso:  python pipeline/run_pipeline.py
Env:  --skip-download   → salta descarga (usa data/raw/ ya existente)
      --fecha 2026-07-21 → sobreescribe la fecha de referencia
"""
from __future__ import annotations
import argparse
import datetime as dt
import logging
import sys
import time
from pathlib import Path

# Añade este directorio al path para que los imports relativos funcionen
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402
from config import LOGS_DIR, RAW_DIR, CLEAN_DIR, METRICS_DIR  # noqa: E402


def setup_logging() -> Path:
    log_file = LOGS_DIR / f"pipeline_{dt.datetime.now():%Y%m%d_%H%M%S}.log"
    fmt = "%(asctime)s %(levelname)-7s %(name)-12s | %(message)s"
    # Fuerza stdout a UTF-8 para que los logs con acentos no rompan en Windows
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[logging.FileHandler(log_file, encoding="utf-8"),
                  logging.StreamHandler(sys.stdout)],
        force=True,
    )
    return log_file


def _step(name: str, fn):
    log = logging.getLogger("pipeline")
    log.info(">>>─ INICIO: %s", name)
    t0 = time.time()
    try:
        out = fn()
        dur = time.time() - t0
        log.info("<<<─ FIN:    %s   OK   (%.1fs)", name, dur)
        return {"ok": True, "duracion_s": round(dur, 1), "detalle": out}
    except Exception as e:
        dur = time.time() - t0
        log.exception("<<<─ FIN:    %s   FAIL (%.1fs): %s", name, dur, e)
        return {"ok": False, "duracion_s": round(dur, 1), "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--fecha", default=None, help="YYYY-MM-DD; default hoy")
    args = parser.parse_args()

    log_file = setup_logging()
    log = logging.getLogger("pipeline")
    log.info("═══════════════ PIPELINE START ═══════════════")
    log.info("Log file: %s", log_file)

    fecha_hoy = pd.Timestamp(args.fecha) if args.fecha else pd.Timestamp.today().normalize()
    log.info("Fecha de referencia: %s", fecha_hoy.date())

    from download_drive     import run as download_run
    from normalize          import run as normalize_run
    from correct_costs      import run as costs_run
    from build_model        import run as build_run
    from calculate_metrics  import run as metrics_run

    results = {}
    if not args.skip_download:
        results["download"] = _step("download_drive", download_run)
    else:
        log.info("(skip-download activo — se usan archivos ya en data/raw/)")
        results["download"] = {"ok": True, "detalle": "skipped"}

    results["normalize"]     = _step("normalize",         lambda: normalize_run(fecha_hoy))
    results["correct_costs"] = _step("correct_costs",     costs_run)
    results["build"]         = _step("build_model",       build_run)
    results["metrics"]       = _step("calculate_metrics", lambda: metrics_run(fecha_hoy))

    # Resumen
    def _count(d):
        return sum(1 for _ in d.iterdir() if _.is_file()) if d.exists() else 0
    raw_n     = _count(RAW_DIR)
    clean_n   = _count(CLEAN_DIR)
    metrics_n = _count(METRICS_DIR)

    n_ok   = sum(1 for r in results.values() if r["ok"])
    n_fail = sum(1 for r in results.values() if not r["ok"])
    log.info("====================== RESUMEN ======================")
    log.info("| Pasos ejecutados: %d   OK: %d   FAIL: %d", len(results), n_ok, n_fail)
    log.info("| data/raw/      : %d archivos", raw_n)
    log.info("| data/clean/    : %d archivos", clean_n)
    log.info("| data/metrics/  : %d archivos", metrics_n)
    for step, r in results.items():
        estado = "OK" if r["ok"] else "FAIL"
        log.info("|   %s  %-8s (%.1fs)  %s", estado, step,
                 r.get("duracion_s", 0), r.get("error", ""))
    log.info("=========================================================")


if __name__ == "__main__":
    main()
