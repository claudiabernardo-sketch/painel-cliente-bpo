"""
Cria um extrato FICTÍCIO no mesmo formato do Conta Azul, para treinar sem dado de cliente:

    python codigo/exemplo.py            gera exemplos/extrato_ficticio_padaria.xls

Empresa fictícia: Padaria Modelo. 12 meses, de novembro de 2025 a outubro de 2026.
Nenhum nome, CNPJ ou valor é real.
"""
from __future__ import annotations

import random
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CABECALHO = ["Data movimento", "Identificador do fornecedor/cliente", "Nome do fornecedor/cliente", "Recorrência",
             "Quantidade de recorrência", "Descrição", "Agendado", "Tipo", "Origem do lançamento", "Conta bancária",
             "Forma de pgto/recbto", "Valor (R$)", "Saldo conta (R$)", "Situação", "Valor original (R$)", "Juros (R$)",
             "Multa (R$)", "Desconto (R$)", "Taxas (R$)", "Data de competência", "Data original de vencimento",
             "Data prevista", "Observações", "Nota fiscal", "Categoria 1", "Valor na Categoria 1"]

RECEITAS = [("Vendas no balcão", "Clientes balcão", 0.55), ("Vendas no cartão", "Maquininha", 0.35),
            ("Encomendas", "Clientes encomenda", 0.10)]
DESPESAS = [  # categoria, fornecedor, valor base mensal
    ("Fornecedores de insumos", "Moinho Exemplo Ltda", 18200), ("Salários", "Folha de pagamento", 9800),
    ("Aluguel", "Imobiliária Exemplo", 4500), ("Energia elétrica", "Companhia de Energia", 2100),
    ("Impostos (Simples Nacional)", "Receita Federal", 2600), ("Embalagens", "Embalagens Exemplo", 1300),
    ("Manutenção", "Técnico Exemplo", 600), ("Tarifas bancárias", "Banco Exemplo", 180),
]


def linhas(semente: int = 7) -> list[list]:
    rnd = random.Random(semente)
    saida = []
    meses = [(2025, 11), (2025, 12)] + [(2026, m) for m in range(1, 11)]
    for i, (a, m) in enumerate(meses):
        sazonal = 1.25 if m == 12 else (0.9 if m in (1, 2) else 1.0)
        faturamento = 46000 * sazonal * (1 + i * 0.006) * rnd.uniform(0.95, 1.05)
        for cat, quem, parte in RECEITAS:
            for semana in range(4):
                v = round(faturamento * parte / 4 * rnd.uniform(0.9, 1.1), 2)
                d = date(a, m, min(28, 3 + semana * 7))
                saida.append([d, "Receita", cat, quem, v])
        for cat, quem, base in DESPESAS:
            v = base * rnd.uniform(0.93, 1.07)
            if cat == "Energia elétrica" and (a, m) == (2026, 10):
                v = base * 1.22 * 1.18  # a energia subiu: aparece nos alertas
            if cat == "Fornecedores de insumos":
                v *= sazonal
            d = date(a, m, {"Salários": 5, "Aluguel": 10, "Impostos (Simples Nacional)": 20}.get(cat, rnd.randint(6, 27)))
            saida.append([d, "Despesa", cat, quem, round(v, 2)])
        # transferência entre contas da própria padaria: não entra nas contas
        saida.append([date(a, m, 15), "Despesa", "Transferência", "Padaria Modelo", 3000.0, "transf"])
        saida.append([date(a, m, 15), "Receita", "Transferência", "Padaria Modelo", 3000.0, "transf"])
    return saida


def gerar(destino: Path | None = None) -> Path:
    import openpyxl
    destino = destino or RAIZ / "exemplos" / "extrato_ficticio_padaria.xls"
    destino.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Extrato Financeiro"
    ws.append(CABECALHO)
    for item in sorted(linhas(), key=lambda x: x[0]):
        d, tipo, cat, quem, v = item[:5]
        transf = len(item) > 5
        valor = v if tipo == "Receita" else -v
        dt = d.strftime("%d/%m/%Y")
        ws.append([dt, "", quem, "Sem recorrência", "", cat if not transf else "Transferência entre contas", "-", tipo,
                   "Transferência" if transf else "Lançamento Financeiro", "Banco Exemplo - Conta Corrente", "Outro",
                   valor, 0, "Transferido" if transf else "Quitado", valor, 0, 0, 0, 0, dt, dt, dt, "", "",
                   "" if transf else cat, None if transf else valor])
    # o Conta Azul exporta um .xlsx com o nome .xls: aqui é igual
    import io
    buf = io.BytesIO()
    wb.save(buf)
    destino.write_bytes(buf.getvalue())
    return destino


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Extrato fictício criado: {gerar()}")
