#!/usr/bin/env python3
"""
Gera uma ficha de conferência dos baremas a partir das amostras coletadas.

Lê tudo que estiver em _amostras/ (gerado pelo _coletar_amostras.py) e produz
_conferencia.html na raiz do projeto: uma página com, para cada currículo, as
séries brutas do CNPq e os quatro baremas item a item, com link direto para a
página oficial de indicadores para comparação visual.

Uso:
    python _relatorio_conferencia.py
"""

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import controller

RAIZ = Path(__file__).resolve().parent.parent
AMOSTRAS = RAIZ / "_amostras"
SAIDA = RAIZ / "_conferencia.html"

# Grupos de séries e a que seção do barema pertencem, para sinalizar suspeitas.
GRUPOS = [
    ("barraAnosProducoesBibliograficas", "Produção bibliográfica"),
    ("barraAnosProducoesTecnicas", "Produção técnica"),
    ("barraAnosPatentes", "Patentes e registros"),
    ("barraAnosProducoesCulturais", "Produções culturais"),
    ("barraAnosOrientacoes", "Orientações"),
]

# Quais chaves de quantidade dependem de qual grupo (para detectar extração falha)
DEPENDENCIAS = {
    "barraAnosProducoesTecnicas": [
        "apresentacao_trabalho", "programa_computador", "produtos",
        "processos", "trabalhos_tecnicos",
    ],
    "barraAnosPatentes": ["patentes", "cultivar"],
    "barraAnosProducoesCulturais": [
        "artes_cenicas", "artes_visuais", "musica", "outras_culturais",
    ],
    "barraAnosOrientacoes": [
        "orientacao_doutorado", "orientacao_mestrado",
        "supervisao_pos_doutorado", "orientacao_demais",
    ],
}

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--linha:#e3e6ea;--txt:#1b1f24;--suave:#5b636d;
--ok:#0f7b3f;--alerta:#a8620a;--erro:#b3261e;--destaque:#eef4ff}
*{box-sizing:border-box}
body{margin:0;padding:32px 20px;background:var(--bg);color:var(--txt);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:1.6rem;margin:0 0 4px}
.sub{color:var(--suave);margin:0 0 28px}
.cv{background:var(--card);border:1px solid var(--linha);border-radius:12px;
padding:22px 24px;margin-bottom:28px}
.cv h2{margin:0 0 2px;font-size:1.25rem}
.meta{color:var(--suave);font-size:.88rem;margin-bottom:14px}
.meta a{color:#0b57d0}
h3{font-size:1rem;margin:22px 0 8px;padding-bottom:6px;border-bottom:2px solid var(--linha)}
h4{font-size:.9rem;margin:16px 0 6px;color:var(--suave);text-transform:uppercase;
letter-spacing:.04em}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{text-align:left;font-weight:600;color:var(--suave);font-size:.78rem;
text-transform:uppercase;letter-spacing:.04em;padding:6px 8px;border-bottom:1px solid var(--linha)}
td{padding:6px 8px;border-bottom:1px solid #f0f2f4}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr.tem td{background:var(--destaque)}
tr.zero td{color:#9aa1a9}
.tag{display:inline-block;padding:1px 7px;border-radius:99px;font-size:.72rem;
font-weight:600;letter-spacing:.02em}
.tag.ok{background:#e6f4ec;color:var(--ok)}
.tag.vazio{background:#eef0f2;color:var(--suave)}
.tag.susp{background:#fdf0e0;color:var(--alerta)}
.tag.manual{background:#fdeceb;color:var(--erro)}
.totais{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 4px}
.total{border:1px solid var(--linha);border-radius:9px;padding:9px 14px;min-width:132px}
.total b{display:block;font-size:1.35rem;line-height:1.2}
.total span{font-size:.76rem;color:var(--suave)}
.aviso{background:#fdf0e0;border-left:3px solid var(--alerta);padding:10px 14px;
border-radius:0 8px 8px 0;font-size:.88rem;margin:12px 0}
.legenda{font-size:.83rem;color:var(--suave);margin-top:8px}
@media(max-width:640px){body{padding:16px 10px}.cv{padding:16px}}
"""


def esc(valor):
    return html.escape(str(valor))


def num(valor):
    valor = float(valor or 0)
    return str(int(valor)) if valor == int(valor) else f"{valor:.2f}".rstrip("0")


def tabela_secao(secao, teto, manual=False):
    itens = (secao or {}).get("itens") or {}
    linhas = []
    for rotulo, item in itens.items():
        classe = "tem" if item["quantidade"] else "zero"
        linhas.append(
            f"<tr class='{classe}'><td>{esc(rotulo)}</td>"
            f"<td class='num'>{num(item['quantidade'])}</td>"
            f"<td class='num'>{num(item['peso'])}</td>"
            f"<td class='num'>{num(item['pontos'])}</td></tr>"
        )
    marca = " <span class='tag manual'>preenchimento manual</span>" if manual else ""
    bruto = num((secao or {}).get("subtotal_bruto"))
    limitado = num((secao or {}).get("subtotal_limitado"))
    return (
        f"<h4>{marca}</h4>" if manual else ""
    ) + (
        "<table><thead><tr><th>Critério</th><th class='num'>Qtd.</th>"
        "<th class='num'>Peso</th><th class='num'>Pontos</th></tr></thead>"
        f"<tbody>{''.join(linhas)}</tbody>"
        f"<tfoot><tr><td><b>Subtotal</b></td><td colspan='2' class='num'>bruto {bruto}</td>"
        f"<td class='num'><b>{limitado}</b> / {teto}</td></tr></tfoot></table>"
    )


def bloco_barema(titulo, maximo, barema, secoes):
    if not barema or not barema.get("success"):
        return f"<h3>{esc(titulo)}</h3><p>Não foi possível calcular.</p>"

    partes = [
        f"<h3>{esc(titulo)} — total {num(barema['total_limitado'])} de {maximo}</h3>"
    ]
    for chave, rotulo, teto, manual in secoes:
        partes.append(f"<h4>{esc(rotulo)}</h4>")
        partes.append(tabela_secao(barema.get(chave), teto, manual))
    return "".join(partes)


def processar(code):
    index_html = (AMOSTRAS / f"{code}.index.html").read_text(encoding="utf-8")
    preview_html = (AMOSTRAS / f"{code}.preview.html").read_text(encoding="utf-8")

    resultado = {
        "success": True, "url": code, "code": code,
        "nome": controller._extrair_nome_pessoa(preview_html),
        "preview_html": preview_html, "index_html": index_html,
        "publicacoes": controller.extract_publications(index_html),
        "message": "ok",
    }

    variaveis = controller._extrair_variaveis_js(index_html)
    quantidades = controller._coletar_quantidades_extensao(
        variaveis, preview_html, index_html
    )

    doc = controller.calcularBaremaExtensaoDocente(resultado)
    dis = controller.calcularBaremaExtensaoDiscente(resultado)
    ic = controller.calcularBarema(resultado)
    aeri = controller.calcularBaremaAERI(resultado)

    partes = ["<div class='cv'>"]
    partes.append(f"<h2>{esc(resultado['nome'] or code)}</h2>")
    url_graficos = (
        "http://buscatextual.cnpq.br/buscatextual/graficos.do"
        f"?metodo=apresentar&codRHCript={code}"
    )
    partes.append(
        f"<div class='meta'>Código {esc(code)} · "
        f"<a href='{esc(url_graficos)}' target='_blank' rel='noopener'>"
        "abrir indicadores oficiais no CNPq</a> para comparar</div>"
    )

    partes.append(
        "<div class='totais'>"
        f"<div class='total'><b>{num(doc.get('total_limitado'))}</b>"
        "<span>PIBEX docente / 40</span></div>"
        f"<div class='total'><b>{num(dis.get('total_limitado'))}</b>"
        "<span>PIBEX discente / 20</span></div>"
        f"<div class='total'><b>{num(ic.get('total_limitado'))}</b>"
        "<span>IC / 60</span></div>"
        f"<div class='total'><b>{num(aeri.get('total_limitado'))}</b>"
        "<span>AERI / 40</span></div>"
        "</div>"
    )

    # --- séries brutas + diagnóstico de grupos ---
    partes.append("<h3>Séries encontradas na página do CNPq</h3>")
    linhas = []
    suspeitas = []
    for grupo, rotulo_grupo in GRUPOS:
        anos = variaveis.get(grupo)
        tem_grupo = bool(anos)
        membros = {
            k: v for k, v in variaveis.items()
            if not k.lower().startswith("barraanos") and k != "barraTodasProducoes"
        }
        if not tem_grupo:
            etiqueta = "<span class='tag vazio'>sem dados no currículo</span>"
        else:
            dependentes = DEPENDENCIAS.get(grupo, [])
            extraido = sum(quantidades.get(c, 0) for c in dependentes) if dependentes else None
            if dependentes and not extraido:
                etiqueta = "<span class='tag susp'>grupo existe mas extração deu zero</span>"
                suspeitas.append(rotulo_grupo)
            else:
                etiqueta = "<span class='tag ok'>com dados</span>"
        linhas.append(
            f"<tr><td><b>{esc(rotulo_grupo)}</b> {etiqueta}</td>"
            f"<td class='num'>{len(anos) if anos else 0} anos</td>"
            "<td></td><td></td></tr>"
        )

    for chave in sorted(variaveis):
        if chave.lower().startswith("barraanos"):
            continue
        total = sum(controller._normalizar_serie(variaveis[chave], 60))
        classe = "tem" if total else "zero"
        linhas.append(
            f"<tr class='{classe}'><td style='padding-left:22px'><code>{esc(chave)}</code></td>"
            f"<td class='num'>{total}</td><td></td><td></td></tr>"
        )
    partes.append(
        "<table><thead><tr><th>Série</th><th class='num'>Total</th>"
        "<th></th><th></th></tr></thead><tbody>"
        + "".join(linhas) + "</tbody></table>"
    )
    partes.append(
        "<p class='legenda'>Compare estes totais com os gráficos da página oficial "
        "do CNPq (link acima). Se algum número divergir, a extração está errada.</p>"
    )

    if suspeitas:
        partes.append(
            "<div class='aviso'><b>Atenção:</b> o currículo tem dados em "
            + esc(", ".join(suspeitas))
            + ", mas o barema extraiu zero desses grupos. Provável erro de mapeamento.</div>"
        )

    ignoradas = {
        k: sum(controller._normalizar_serie(variaveis[k], 60))
        for k in variaveis
        if not k.lower().startswith("barraanos")
        and "citacoes" not in k.lower()
        and k != "barraTodasProducoes"
    }
    nao_usadas = {
        k: v for k, v in ignoradas.items()
        if v and "OutrasProducoesTecnicas" in k
    }
    if nao_usadas:
        detalhe = ", ".join(f"{esc(k)} ({v})" for k, v in nao_usadas.items())
        partes.append(
            "<div class='aviso'><b>Decisão do CIBEX:</b> o currículo tem "
            f"{detalhe}, que o Anexo II não lista em nenhum item de produção "
            "técnica. Hoje esses itens não pontuam. Confirme se é essa a intenção.</div>"
        )

    partes.append(bloco_barema("PIBEX — Barema A (docente/orientador)", 40, doc, [
        ("titulacao", "I - Titulação", 4, False),
        ("atuacao_extensao", "II - Atuação na extensão", 8, True),
        ("producao", "III - Indicadores de produção", 18, False),
        ("formacao_recursos_humanos", "IV - Formação de recursos humanos", 10, False),
    ]))
    partes.append(bloco_barema("PIBEX — Barema B (discente/candidato)", 20, dis, [
        ("atuacao_extensao", "I - Atuação na extensão", 6, True),
        ("producao", "II - Indicadores de produção", 5, False),
        ("participacao_eventos", "III - Participação/organização de eventos", 9, True),
    ]))

    partes.append("</div>")
    return "".join(partes)


def main():
    if not AMOSTRAS.exists():
        print(f"Pasta não encontrada: {AMOSTRAS}")
        print("Rode antes: python _coletar_amostras.py <codigo do lattes>")
        return 1

    codes = sorted(p.name[:-len(".index.html")] for p in AMOSTRAS.glob("*.index.html"))
    if not codes:
        print(f"Nenhuma amostra em {AMOSTRAS}.")
        return 1

    print(f"Gerando ficha para {len(codes)} currículo(s)...")
    corpo = "".join(processar(code) for code in codes)

    pagina = (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Conferência dos baremas — PontuaLattes</title>"
        f"<style>{CSS}</style></head><body><div class='wrap'>"
        "<h1>Conferência dos baremas</h1>"
        "<p class='sub'>Quantidades extraídas do Lattes e pontuação calculada, "
        "para comparação com a página oficial do CNPq e com o Anexo II do edital.</p>"
        f"{corpo}</div></body></html>"
    )

    SAIDA.write_text(pagina, encoding="utf-8")
    print(f"Pronto: {SAIDA}")
    for code in codes:
        print(f"  - {code}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
