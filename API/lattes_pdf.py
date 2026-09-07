# pyright: reportMissingImports=false
"""
Extração de dados do PDF do Currículo Lattes.

Complementa a página pública de indicadores do CNPq, que só expõe contagens de
produção. O PDF do currículo completo traz o que falta para o barema PIBEX:
participação e organização de eventos, e projetos de extensão com o papel de
cada integrante.

Depende de pdfplumber (pip install pdfplumber).
"""

import re
import unicodedata


# ---------------------------------------------------------------------------
# Leitura do PDF
# ---------------------------------------------------------------------------

def extrair_texto(origem):
	"""Recebe caminho, bytes ou objeto de arquivo e devolve o texto do PDF."""
	import io

	import pdfplumber

	if isinstance(origem, (bytes, bytearray)):
		origem = io.BytesIO(origem)

	paginas = []
	with pdfplumber.open(origem) as pdf:
		for pagina in pdf.pages:
			paginas.append(pagina.extract_text() or "")

	return "\n".join(paginas)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sem_acento(texto):
	normalizado = unicodedata.normalize("NFKD", str(texto or ""))
	return "".join(c for c in normalizado if not unicodedata.combining(c)).lower()


def _linhas(texto):
	return [linha.rstrip() for linha in (texto or "").split("\n")]


def _indice_secao(linhas, titulo):
	"""Índice da linha cujo conteúdo é exatamente o título da seção."""
	alvo = _sem_acento(titulo).strip()
	for indice, linha in enumerate(linhas):
		if _sem_acento(linha).strip() == alvo:
			return indice
	return None


# Cabeçalhos de primeiro nível do currículo, usados para delimitar seções.
_SECOES_RAIZ = [
	"Identificação", "Endereço", "Formação acadêmica/titulação", "Pós-doutorado",
	"Formação Complementar", "Atuação Profissional", "Linhas de pesquisa",
	"Projetos de pesquisa", "Projetos de extensão", "Projetos de desenvolvimento",
	"Projetos de ensino", "Projetos de outra natureza",
	"Membro de comitê de assessoramento", "Revisor de periódico",
	"Áreas de atuação", "Idiomas", "Prêmios e títulos", "Produções", "Bancas",
	"Eventos", "Orientações", "Inovação", "Educação e Popularização de C & T",
	"Outras informações relevantes",
]


def _fim_da_secao(linhas, inicio, extras=()):
	"""Onde termina o bloco iniciado em `inicio`: no próximo cabeçalho conhecido."""
	limites = {_sem_acento(t).strip() for t in list(_SECOES_RAIZ) + list(extras)}
	for indice in range(inicio + 1, len(linhas)):
		if _sem_acento(linhas[indice]).strip() in limites:
			return indice
	return len(linhas)


def _contar_itens(bloco):
	"""Conta itens numerados do Lattes ("1.", "2.", ... em linha própria).

	Usa a maior sequência contígua a partir de 1, o que evita contar anos e
	outros números soltos que aparecem no meio do texto.
	"""
	numeros = {int(n) for n in re.findall(r"^\s*(\d+)\.\s*$", bloco, re.M)}
	total = 0
	while total + 1 in numeros:
		total += 1
	return total


# ---------------------------------------------------------------------------
# Nome do titular
# ---------------------------------------------------------------------------

def extrair_nome(texto):
	for linha in _linhas(texto)[:12]:
		limpo = linha.strip()
		if not limpo or "lattes" in limpo.lower() or "cnpq" in limpo.lower():
			continue
		if re.fullmatch(r"[A-Za-zÀ-ÿ'´`^~. -]{6,90}", limpo):
			return limpo
	return None


# ---------------------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------------------

_SUBSECOES_EVENTOS = (
	"Participação em eventos, congressos, exposições e feiras",
	"Organização de eventos, congressos, exposições e feiras",
)


def extrair_eventos(texto):
	linhas = _linhas(texto)
	resultado = {"participacao_eventos": 0, "organizacao_eventos": 0}

	chaves = dict(zip(_SUBSECOES_EVENTOS, ("participacao_eventos", "organizacao_eventos")))
	for titulo, chave in chaves.items():
		inicio = _indice_secao(linhas, titulo)
		if inicio is None:
			continue
		fim = _fim_da_secao(linhas, inicio, extras=_SUBSECOES_EVENTOS)
		resultado[chave] = _contar_itens("\n".join(linhas[inicio:fim]))

	return resultado


# ---------------------------------------------------------------------------
# Projetos
# ---------------------------------------------------------------------------

_PERIODO = re.compile(r"^((?:19|20)\d{2})\s*-\s*((?:19|20)\d{2}|Atual)\s*$", re.I)


def _juntar(linhas):
	return re.sub(r"\s+", " ", " ".join(linhas)).strip()


def extrair_projetos(texto, titulo_secao="Projetos de extensão", nome_titular=None):
	"""Lista os projetos de uma seção, com papel do titular e duração em anos."""
	linhas = _linhas(texto)
	inicio = _indice_secao(linhas, titulo_secao)
	if inicio is None:
		return []

	fim = _fim_da_secao(linhas, inicio)
	corpo = linhas[inicio + 1:fim]

	# Cada projeto começa numa linha de período ("2020 - 2022" / "2024 - Atual")
	inicios = [i for i, linha in enumerate(corpo) if _PERIODO.match(linha.strip())]
	if not inicios:
		return []

	nome_titular = _sem_acento(nome_titular or extrair_nome(texto) or "")
	ano_corrente_padrao = 2026

	projetos = []
	for ordem, i in enumerate(inicios):
		j = inicios[ordem + 1] if ordem + 1 < len(inicios) else len(corpo)
		periodo = _PERIODO.match(corpo[i].strip())
		bloco = _juntar(corpo[i:j])

		ano_inicial = int(periodo.group(1))
		fim_texto = periodo.group(2)
		ano_final = ano_corrente_padrao if fim_texto.lower() == "atual" else int(fim_texto)
		duracao = max(0, ano_final - ano_inicial)

		papel = None
		integrantes = re.search(r"Integrantes:\s*(.+?)(?:\.\s|$)", bloco)
		if integrantes and nome_titular:
			for parte in integrantes.group(1).split("/"):
				if "-" not in parte:
					continue
				pessoa, _, funcao = parte.rpartition("-")
				if nome_titular and nome_titular in _sem_acento(pessoa):
					papel = funcao.strip().strip(".").strip()
					break

		titulo = _juntar(corpo[i + 1:i + 4])
		titulo = re.split(r"Descrição:|Situação:", titulo)[0].strip()

		projetos.append({
			"titulo": titulo[:160],
			"ano_inicial": ano_inicial,
			"ano_final": ano_final,
			"duracao_anos": duracao,
			"papel": papel,
			"concluido": "concluido" in _sem_acento(bloco),
		})

	return projetos


def classificar_projetos_extensao(projetos):
	"""Traduz os projetos para as quatro linhas da seção de atuação na extensão
	do barema docente (Anexo II-A, item II)."""
	contagem = {
		"coordenacao_ate_2_anos": 0,
		"coordenacao_acima_2_anos": 0,
		"integrante_ate_2_anos": 0,
		"integrante_acima_2_anos": 0,
		"papel_indefinido": 0,
	}

	for projeto in projetos:
		papel = _sem_acento(projeto.get("papel") or "")
		acima = (projeto.get("duracao_anos") or 0) > 2

		if "coordenador" in papel:
			chave = "coordenacao_acima_2_anos" if acima else "coordenacao_ate_2_anos"
		elif "integrante" in papel:
			chave = "integrante_acima_2_anos" if acima else "integrante_ate_2_anos"
		else:
			chave = "papel_indefinido"

		contagem[chave] += 1

	return contagem


# ---------------------------------------------------------------------------
# API principal
# ---------------------------------------------------------------------------

def extrair_do_pdf(origem):
	"""Devolve tudo que o PDF acrescenta ao que já vem da página de indicadores."""
	texto = extrair_texto(origem)
	nome = extrair_nome(texto)

	projetos = extrair_projetos(texto, "Projetos de extensão", nome)

	dados = {"nome": nome, "projetos_extensao": projetos}
	dados.update(extrair_eventos(texto))
	dados.update(classificar_projetos_extensao(projetos))
	return dados
