"""
Lê o extrato financeiro exportado do Conta Azul (extrato_financeiro.xls).

O arquivo vem com a extensão .xls, mas por dentro é um Excel moderno (.xlsx):
por isso ele é aberto pelo conteúdo, não pelo nome.

Colunas usadas (como o Conta Azul exporta):
  Data movimento, Tipo (Receita / Despesa), Valor (R$), Situação,
  Origem do lançamento, Nome do fornecedor/cliente, Descrição,
  Conta bancária, Data de competência, Categoria 1 / Valor na Categoria 1,
  Categoria 2 / Valor na Categoria 2 ... (quando o lançamento é rateado).

Transferência entre contas do próprio cliente (Situação "Transferido" ou
Origem "Transferência") não é receita nem despesa: fica de fora das contas.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

OBRIGATORIAS = ["Data movimento", "Tipo", "Valor (R$)"]


class ArquivoInvalido(Exception):
    """O arquivo não é o extrato financeiro do Conta Azul. A mensagem diz o que fazer."""


@dataclass
class Lancamento:
    data: date
    tipo: str                      # "Receita" ou "Despesa"
    valor: Decimal                 # sempre positivo
    transferencia: bool
    situacao: str = ""
    competencia: date | None = None
    contraparte: str = ""
    descricao: str = ""
    conta: str = ""
    categorias: list[tuple[str, Decimal]] = field(default_factory=list)


def _data(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", str(v or ""))
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _valor(v) -> Decimal | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    s = str(v).replace("R$", "").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _texto(v) -> str:
    return "" if v is None else str(v).strip()


def ler(caminho: str | Path) -> list[Lancamento]:
    import openpyxl
    caminho = Path(caminho)
    dados = caminho.read_bytes()
    if not dados.startswith(b"PK"):
        raise ArquivoInvalido(
            f"{caminho.name} não é o extrato do Conta Azul em Excel. "
            "Exporte de novo pelo Conta Azul, em Excel, sem abrir e salvar o arquivo antes.")
    wb = openpyxl.load_workbook(io.BytesIO(dados), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    linhas = ws.iter_rows(values_only=True)
    cab = [_texto(c) for c in next(linhas, [])]
    faltam = [c for c in OBRIGATORIAS if c not in cab]
    if faltam:
        raise ArquivoInvalido(
            f"{caminho.name} não tem as colunas {', '.join(faltam)}. "
            "Este painel lê o EXTRATO FINANCEIRO do Conta Azul (o arquivo extrato_financeiro.xls).")
    col = {nome: i for i, nome in enumerate(cab)}
    pares_cat = []
    for nome, i in col.items():
        m = re.fullmatch(r"Categoria (\d+)", nome)
        if m and f"Valor na Categoria {m.group(1)}" in col:
            pares_cat.append((int(m.group(1)), i, col[f"Valor na Categoria {m.group(1)}"]))
    pares_cat.sort()

    def pega(linha, nome):
        i = col.get(nome)
        return linha[i] if i is not None and i < len(linha) else None

    saida = []
    for linha in linhas:
        d = _data(pega(linha, "Data movimento"))
        v = _valor(pega(linha, "Valor (R$)"))
        tipo = _texto(pega(linha, "Tipo"))
        if d is None or v is None or tipo not in ("Receita", "Despesa"):
            continue
        situacao = _texto(pega(linha, "Situação"))
        origem = _texto(pega(linha, "Origem do lançamento"))
        valor = abs(v)
        cats = []
        for _, ic, iv in pares_cat:
            nome = _texto(linha[ic] if ic < len(linha) else None)
            vc = _valor(linha[iv] if iv < len(linha) else None)
            if nome and vc is not None:
                cats.append((nome, abs(vc)))
        if not cats:
            cats = [("Sem categoria", valor)]
        saida.append(Lancamento(
            data=d, tipo=tipo, valor=valor,
            transferencia=situacao == "Transferido" or origem == "Transferência",
            situacao=situacao, competencia=_data(pega(linha, "Data de competência")),
            contraparte=_texto(pega(linha, "Nome do fornecedor/cliente")),
            descricao=_texto(pega(linha, "Descrição")), conta=_texto(pega(linha, "Conta bancária")),
            categorias=cats,
        ))
    if not saida:
        raise ArquivoInvalido(f"{caminho.name} não tem nenhum lançamento de receita ou despesa.")
    return saida
