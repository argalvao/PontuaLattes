#!/usr/bin/env python3
"""
Testa a extração do PDF do Currículo Lattes.

Mostra o que o PDF acrescenta ao que já vem da página pública de indicadores:
participação e organização de eventos, e projetos de extensão com papel e
duração de cada um.

Uso:
    python _testar_pdf.py "C:\\caminho\\curriculo.pdf"

Requer: pip install pdfplumber
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    if len(sys.argv) < 2:
        print("Informe o caminho do PDF do currículo Lattes.")
        print('Exemplo: python _testar_pdf.py "C:\\Users\\voce\\Downloads\\curriculo.pdf"')
        return 1

    caminho = Path(sys.argv[1])
    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}")
        return 1

    try:
        import lattes_pdf
    except ImportError as erro:
        print(f"Falha ao importar o extrator: {erro}")
        return 1

    try:
        dados = lattes_pdf.extrair_do_pdf(str(caminho))
    except ImportError:
        print("Falta a biblioteca pdfplumber. Instale com:")
        print("    pip install pdfplumber")
        return 1

    print(f"Arquivo: {caminho.name}")
    print(f"Titular: {dados['nome'] or '(não identificado)'}")
    print()
    print("=" * 64)
    print("O QUE O PDF ACRESCENTA (não existe na página de indicadores)")
    print("=" * 64)
    print()
    print("  Barema discente — III, Participação/organização de eventos")
    print(f"      Participação em eventos ........... {dados['participacao_eventos']}"
          f"   ({dados['participacao_eventos'] * 0.5:g} pts, teto 5)")
    print(f"      Organização de eventos ............ {dados['organizacao_eventos']}"
          f"   ({min(dados['organizacao_eventos'], 2):g} pts, teto 2)")
    print()
    print("  Barema docente — II, Atuação na extensão")
    projetos = dados["projetos_extensao"]
    if not projetos:
        print("      Nenhum projeto de extensão no currículo.")
    else:
        print(f"      Coordenação até 2 anos ............ {dados['coordenacao_ate_2_anos']}")
        print(f"      Coordenação acima de 2 anos ....... {dados['coordenacao_acima_2_anos']}")
        print(f"      Integrante até 2 anos ............. {dados['integrante_ate_2_anos']}")
        print(f"      Integrante acima de 2 anos ........ {dados['integrante_acima_2_anos']}")
        if dados["papel_indefinido"]:
            print(f"      (!) papel não identificado em ...... {dados['papel_indefinido']}")
        print()
        print("      Projetos encontrados:")
        for projeto in projetos:
            print(f"        {projeto['ano_inicial']}-{projeto['ano_final']}"
                  f" ({projeto['duracao_anos']} anos)  {projeto['papel'] or 'papel?'}"
                  f"  {projeto['titulo'][:56]}")
    print()
    print("Confira contra o PDF aberto. Se algum número divergir, me avise.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
