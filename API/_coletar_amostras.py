#!/usr/bin/env python3
"""
Coleta amostras reais do Lattes para conferência do barema.

Baixa, para cada currículo informado, a página de índices de produção e o
preview do CNPq, e salva tudo em _amostras/ na raiz do projeto. Nenhum dado
é enviado para lugar nenhum — os arquivos ficam na sua máquina.

Uso:
    python _coletar_amostras.py 3569271948805982 0123456789012345 ...

Aceita URL completa ou só o código público do Lattes.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import controller
from service import getLattesCode, getLattesIndexHtml, getLattesPViewHtml

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "_amostras"


def coletar(entrada):
    print(f"\n[{entrada}]")
    print("  buscando código interno...", end=" ", flush=True)

    code = getLattesCode(entrada)
    if not code or controller._is_request_error(code):
        print(f"FALHOU\n  -> {code}")
        return False

    print(code)

    print("  baixando índices de produção...", end=" ", flush=True)
    index_html = getLattesIndexHtml(code)
    if not index_html:
        print("FALHOU")
        return False
    print(f"{len(index_html)} bytes")

    print("  baixando preview...", end=" ", flush=True)
    preview_html = getLattesPViewHtml(code) or ""
    print(f"{len(preview_html)} bytes")

    variaveis = controller._extrair_variaveis_js(index_html)
    nome = controller._extrair_nome_pessoa(preview_html) or "(sem nome)"

    resumo = {}
    for chave, valores in variaveis.items():
        if chave.lower().startswith("barraanos"):
            resumo[chave] = valores
        else:
            serie = controller._normalizar_serie(valores, 60)
            resumo[chave] = {"total": sum(serie), "serie": serie[:40]}

    dados = {
        "entrada": str(entrada),
        "code": code,
        "nome": nome,
        "titulacao_detectada": controller._calcular_titulacao_extensao(preview_html),
        "variaveis": resumo,
    }

    DESTINO.mkdir(exist_ok=True)
    (DESTINO / f"{code}.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (DESTINO / f"{code}.index.html").write_text(index_html, encoding="utf-8")
    (DESTINO / f"{code}.preview.html").write_text(preview_html, encoding="utf-8")

    produtivas = {
        k: v["total"]
        for k, v in resumo.items()
        if isinstance(v, dict) and v.get("total")
    }
    print(f"  nome: {nome}")
    print(f"  titulação: {dados['titulacao_detectada'][0]}")
    print(f"  {len(variaveis)} séries encontradas, {len(produtivas)} com produção:")
    for chave in sorted(produtivas, key=lambda c: -produtivas[c]):
        print(f"      {chave:52s} {produtivas[chave]}")
    return True


def main():
    entradas = sys.argv[1:]
    if not entradas:
        print("Informe um ou mais códigos/URLs do Lattes.")
        print("Exemplo: python _coletar_amostras.py 3569271948805982")
        return 1

    print(f"Coletando {len(entradas)} currículo(s). Os arquivos vão para:")
    print(f"  {DESTINO}")

    ok = sum(1 for entrada in entradas if coletar(entrada))

    print()
    print("=" * 60)
    print(f"{ok} de {len(entradas)} currículo(s) coletados com sucesso.")
    if ok:
        print(f"Arquivos salvos em: {DESTINO}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
