#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""
Sincroniza todos os dados do banco Turso para uma planilha Google Sheets.

Uso:
    python sync_to_sheets.py

Variáveis de ambiente necessárias (pode usar um arquivo .env):
    TURSO_URL
    TURSO_AUTH_TOKEN
    GOOGLE_SHEETS_SPREADSHEET_ID
    GOOGLE_SERVICE_ACCOUNT_JSON   (string JSON ou base64 da Service Account)

Abas geradas/atualizadas na planilha:
    barema                    – pontuações IC
    barema_aeri               – pontuações AERI
    barema_extensao_docente   – pontuações PIBEX (docente)
    barema_extensao_discente  – pontuações PIBEX (discente)
    consultas                 – histórico de consultas
    editais                   – editais cadastrados
"""

import os
import sys
from pathlib import Path

# Carrega .env do projeto se existir
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _check_env():
    required = [
        "TURSO_URL",
        "TURSO_AUTH_TOKEN",
        "GOOGLE_SHEETS_SPREADSHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
    ]
    missing = [v for v in required if not os.getenv(v, "").strip()]
    if missing:
        print(f"[ERRO] Variáveis de ambiente ausentes: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def run():
    _check_env()

    # Importações locais (evita erro de import antes de .env estar carregado)
    from turso_store import (
        dump_barema, dump_barema_aeri, dump_consultas, dump_editais,
        dump_barema_extensao_docente, dump_barema_extensao_discente,
    )
    from google_sheets_store import sync_all

    print("Lendo dados do Turso...")
    barema_rows          = dump_barema()
    barema_aeri_rows     = dump_barema_aeri()
    barema_ext_doc_rows  = dump_barema_extensao_docente()
    barema_ext_dis_rows  = dump_barema_extensao_discente()
    consultas_rows       = dump_consultas()
    editais_rows         = dump_editais()

    print(
        f"  barema:                   {len(barema_rows)} registros\n"
        f"  barema_aeri:              {len(barema_aeri_rows)} registros\n"
        f"  barema_extensao_docente:  {len(barema_ext_doc_rows)} registros\n"
        f"  barema_extensao_discente: {len(barema_ext_dis_rows)} registros\n"
        f"  consultas:                {len(consultas_rows)} registros\n"
        f"  editais:                  {len(editais_rows)} registros"
    )

    print("Sincronizando com o Google Sheets...")
    sync_all(
        barema_rows,
        barema_aeri_rows,
        barema_ext_doc_rows,
        barema_ext_dis_rows,
        consultas_rows,
        editais_rows,
    )

    print("Sincronização concluída com sucesso.")


if __name__ == "__main__":
    run()
