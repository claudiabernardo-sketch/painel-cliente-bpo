"""
Monta o dashboard do mês do cliente a partir do extrato financeiro do Conta Azul.

    python codigo/painel.py <extrato.xls> --cliente "Padaria Modelo" [--mes 2026-11] [--senha]

Gera, na pasta saida/<cliente>/:
  painel-<aaaa-mm>.html            o dashboard aberto, para mandar como ARQUIVO (WhatsApp, e-mail)
  trancado/index.html              (com --senha) a versão TRANCADA, para publicar como LINK

Regime de caixa: o mês é o da data do pagamento ou recebimento ("Data movimento").
Transferência entre contas do próprio cliente não entra.
Não usa internet e não gasta token da IA.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))

from ler_ca import Lancamento, ler  # noqa: E402

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
MES_CURTO = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
PADRAO = {"nome_bpo": "Seu BPO Financeiro", "cor_principal": "#0B1B33", "cor_destaque": "#2EA8E6",
          "contato": ""}


def e(s) -> str:
    return html.escape(str(s or ""))


def reais(v: Decimal, sinal: bool = False) -> str:
    neg = v < 0
    inteiro, cent = f"{abs(v):.2f}".split(".")
    grupos = []
    while inteiro:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    txt = f"R$ {'.'.join(grupos) or '0'},{cent}"
    return ("- " if neg else ("+ " if sinal and v > 0 else "")) + txt


def pct(v: Decimal) -> str:
    return f"{v:+.0f}%".replace("+", "+ ").replace("-", "- ")


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "cliente"


def config_bpo(raiz: Path = RAIZ) -> dict:
    cfg = dict(PADRAO)
    arq = raiz / "bpo.json"
    if arq.exists():
        cfg.update({k: v for k, v in json.loads(arq.read_text(encoding="utf-8")).items() if not k.startswith("_")})
    for chave in ("cor_principal", "cor_destaque"):
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(cfg.get(chave, ""))):
            cfg[chave] = PADRAO[chave]
    return cfg


# --------------------------------------------------------------------------
# Números
# --------------------------------------------------------------------------

def chave_mes(d: date) -> tuple[int, int]:
    return (d.year, d.month)


def mes_anterior(m: tuple[int, int], n: int = 1) -> tuple[int, int]:
    a, mm = m
    total = a * 12 + (mm - 1) - n
    return (total // 12, total % 12 + 1)


def calcular(lancs: list[Lancamento], mes: tuple[int, int] | None = None, hoje: date | None = None) -> dict:
    validos = [x for x in lancs if not x.transferencia]
    if not validos:
        raise ValueError("o extrato só tem transferências entre contas: nada para mostrar")
    meses_com_dado = sorted({chave_mes(x.data) for x in validos})
    ref = mes or meses_com_dado[-1]
    hoje = hoje or date.today()
    # sem mês pedido: o mês em andamento ainda não fechou, então mostra o último mês completo
    if mes is None and ref == chave_mes(hoje) and len(meses_com_dado) > 1:
        ref = meses_com_dado[-2]
    if ref not in meses_com_dado:
        raise ValueError(f"o extrato não tem lançamentos em {ref[1]:02d}/{ref[0]}")

    entradas = defaultdict(Decimal)
    saidas = defaultdict(Decimal)
    cat_desp = defaultdict(lambda: defaultdict(Decimal))
    cat_rec = defaultdict(lambda: defaultdict(Decimal))
    for x in validos:
        m = chave_mes(x.data)
        if x.tipo == "Receita":
            entradas[m] += x.valor
            for nome, v in x.categorias:
                cat_rec[m][nome] += v
        else:
            saidas[m] += x.valor
            for nome, v in x.categorias:
                cat_desp[m][nome] += v

    serie = [mes_anterior(ref, n) for n in range(11, -1, -1)]
    serie = [m for m in serie if m >= meses_com_dado[0]]
    ent, sai = entradas[ref], saidas[ref]
    res = ent - sai
    ant = mes_anterior(ref)
    tem_ant = ant in entradas or ant in saidas

    def variacao(atual, antes):
        return None if not antes else (atual - antes) / antes * 100

    # alertas
    alertas = []
    if res < 0:
        alertas.append(f"O mês fechou no negativo: saiu {reais(-res)} a mais do que entrou.")
    for nome, v in sorted(cat_desp[ref].items(), key=lambda kv: -kv[1]):
        anteriores = [cat_desp[mes_anterior(ref, n)].get(nome, Decimal(0)) for n in (1, 2, 3)]
        base = [a for a in anteriores if a > 0]
        if len(base) >= 2:
            media = sum(base) / len(base)
            if v > media * Decimal("1.25") and v - media >= Decimal(300):
                alertas.append(f"O gasto com {nome} subiu {(v - media) / media * 100:.0f}% contra a média dos meses "
                               f"anteriores ({reais(v)} contra {reais(media)}).")
        if len(alertas) >= 4:
            break
    if tem_ant and entradas[ant] and ent < entradas[ant] * Decimal("0.8"):
        alertas.append(f"As entradas caíram {(entradas[ant] - ent) / entradas[ant] * 100:.0f}% contra o mês anterior.")

    maiores = sorted([x for x in validos if x.tipo == "Despesa" and chave_mes(x.data) == ref],
                     key=lambda x: -x.valor)[:5]
    serie_ok = [(m, entradas[m] - saidas[m]) for m in serie]
    ultimo_dia = max(x.data for x in validos if chave_mes(x.data) == ref)
    return {
        "positivos": sum(1 for _, r in serie_ok if r >= 0), "negativos": sum(1 for _, r in serie_ok if r < 0),
        "ate": ultimo_dia, "ant": ant if tem_ant else None,
        "ref": ref, "entradas": ent, "saidas": sai, "resultado": res,
        "margem": (res / ent * 100) if ent else None,
        "var_entradas": variacao(ent, entradas.get(ant)) if tem_ant else None,
        "var_saidas": variacao(sai, saidas.get(ant)) if tem_ant else None,
        "serie": [(m, entradas[m], saidas[m]) for m in serie],
        "cat_desp": sorted(cat_desp[ref].items(), key=lambda kv: -kv[1]),
        "cat_rec": sorted(cat_rec[ref].items(), key=lambda kv: -kv[1]),
        "maiores": maiores, "alertas": alertas,
        "lancamentos": sum(1 for x in validos if chave_mes(x.data) == ref),
    }


# --------------------------------------------------------------------------
# Página
# --------------------------------------------------------------------------

def grafico(serie, cor_ent: str, cor_sai: str) -> str:
    if not serie:
        return ""
    larg, alt, base = 900, 260, 220
    maior = max([max(a, b) for _, a, b in serie] + [Decimal(1)])
    passo = larg / len(serie)
    barra = min(28, passo / 3)
    partes = []
    for i, ((a, m), en, sa) in enumerate(serie):
        x = i * passo + passo / 2
        for j, (v, cor) in enumerate(((en, cor_ent), (sa, cor_sai))):
            h = float(v / maior) * (base - 20)
            partes.append(f'<rect x="{x - barra - 2 + j * (barra + 4):.1f}" y="{base - h:.1f}" width="{barra:.1f}" '
                          f'height="{h:.1f}" rx="4" fill="{cor}"><title>{e(reais(v))}</title></rect>')
        partes.append(f'<text x="{x:.1f}" y="{base + 22}" text-anchor="middle" font-size="13" fill="#64748B">'
                      f'{MES_CURTO[m - 1]}/{str(a)[2:]}</text>')
    partes.append(f'<line x1="0" y1="{base}" x2="{larg}" y2="{base}" stroke="#E2E8F0" stroke-width="2"/>')
    return (f'<svg viewBox="0 0 {larg} {alt}" width="100%" role="img" '
            f'aria-label="Entradas e saídas dos últimos meses">{"".join(partes)}</svg>')


def barras(itens, total: Decimal, cor: str, limite: int = 7) -> str:
    if not itens:
        return '<p class="vazio">Sem lançamentos no mês.</p>'
    mostra = list(itens[:limite])
    resto = sum((v for _, v in itens[limite:]), Decimal(0))
    if resto:
        mostra.append(("Outras", resto))
    maior = max(v for _, v in mostra) or Decimal(1)
    linhas = []
    for nome, v in mostra:
        p = (v / total * 100) if total else Decimal(0)
        linhas.append(f'<div class="bar"><div class="bar-top"><span>{e(nome)}</span><b>{reais(v)} '
                      f'<small>{p:.0f}%</small></b></div><div class="trilho"><div class="cheio" '
                      f'style="width:{float(v / maior * 100):.1f}%;background:{cor}"></div></div></div>')
    return "".join(linhas)


def resumo(dados: dict) -> list[str]:
    a, m = dados["ref"]
    res = dados["resultado"]
    frases = [f"Em {MESES[m - 1]}, entrou {reais(dados['entradas'])} e saiu {reais(dados['saidas'])}: "
              + (f"sobrou {reais(res)}." if res >= 0 else f"faltou {reais(-res)}.")]
    if dados["cat_desp"] and dados["saidas"]:
        nome, v = dados["cat_desp"][0]
        frases.append(f"O maior gasto foi {nome}: {reais(v)}, {v / dados['saidas'] * 100:.0f}% de tudo o que saiu.")
    if dados["ant"]:
        mes_ant = MESES[dados["ant"][1] - 1]
        partes = []
        if dados["var_entradas"] is not None:
            partes.append(f"as entradas {'subiram' if dados['var_entradas'] >= 0 else 'caíram'} {abs(dados['var_entradas']):.0f}%")
        if dados["var_saidas"] is not None:
            partes.append(f"as saídas {'subiram' if dados['var_saidas'] >= 0 else 'caíram'} {abs(dados['var_saidas']):.0f}%")
        if partes:
            frases.append(f"Comparado a {mes_ant}, " + " e ".join(partes) + ".")
    return frases


def montar(dados: dict, cliente: str, cfg: dict, gerado_em: datetime | None = None, comentario: str = "") -> str:
    a, m = dados["ref"]
    cor, dest = cfg["cor_principal"], cfg["cor_destaque"]
    res = dados["resultado"]
    gerado_em = gerado_em or datetime.now()
    frases = "".join(f"<li>{e(f)}</li>" for f in resumo(dados))
    n_meses = dados["positivos"] + dados["negativos"]
    historico = (f"Nos últimos {n_meses} meses, sobrou dinheiro em {dados['positivos']} e faltou em {dados['negativos']}."
                 if n_meses > 1 else "")
    bloco_comentario = ""
    if comentario.strip():
        paragrafos = "".join(f"<p>{e(p)}</p>" for p in comentario.strip().split("\n") if p.strip())
        bloco_comentario = (f'<section class="comentario"><h2>O que o seu BPO recomenda?</h2>{paragrafos}'
                            f'<p class="assina">{e(cfg["nome_bpo"])}</p></section>')

    def var(v, bom_se_sobe=True):
        if v is None:
            return '<p class="sub">sem mês anterior para comparar</p>'
        boa = (v >= 0) == bom_se_sobe
        return f'<p class="sub {"ok" if boa else "ruim"}">{pct(v)} contra o mês anterior</p>'

    margem = "" if dados["margem"] is None else f'<p class="sub">{dados["margem"]:.0f}% do que entrou</p>'
    alertas = "".join(f"<li>{e(t)}</li>" for t in dados["alertas"]) or "<li>Nenhum alerta neste mês.</li>"
    maiores = "".join(
        f"<tr><td>{x.data:%d/%m}</td><td>{e(x.contraparte or x.descricao or '-')}"
        f"<div class=\"cat\">{e(', '.join(n for n, _ in x.categorias))}</div></td><td class=\"dir\">{reais(x.valor)}</td></tr>"
        for x in dados["maiores"])
    contato = f" · {e(cfg['contato'])}" if cfg.get("contato") else ""

    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{e(cliente)} · {MESES[m - 1]} de {a}</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:"Segoe UI",Inter,Roboto,Arial,sans-serif;background:#F1F5F9;color:#1E293B}}
header{{background:{cor};color:#fff;padding:26px 22px 30px}}
.topo{{max-width:980px;margin:0 auto}}
.bpo{{font-size:13px;letter-spacing:2px;text-transform:uppercase;opacity:.8;margin:0}}
h1{{margin:8px 0 4px;font-size:28px}}
.periodo{{margin:0;font-size:16px;opacity:.9}}
main{{max-width:980px;margin:-18px auto 0;padding:0 16px 30px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}}
.card{{background:#fff;border-radius:16px;padding:18px 20px;box-shadow:0 6px 18px rgba(15,23,42,.07);border-top:5px solid {dest}}}
.card.res{{border-top-color:{'#16A34A' if res >= 0 else '#DC2626'}}}
.rot{{margin:0;font-size:14px;color:#64748B;font-weight:600}}
.num{{margin:6px 0 2px;font-size:28px;font-weight:800}}
.sub{{margin:0;font-size:13px;color:#64748B}} .ok{{color:#15803D}} .ruim{{color:#B91C1C}}
section{{background:#fff;border-radius:16px;padding:20px;margin-top:16px;box-shadow:0 6px 18px rgba(15,23,42,.05)}}
h2{{margin:0 0 14px;font-size:18px;color:{cor}}}
.legenda{{display:flex;gap:18px;font-size:13px;color:#475569;margin-bottom:6px}}
.legenda i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
.duas{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .duas section{{margin-top:16px}}
.bar{{margin-bottom:12px}} .bar-top{{display:flex;justify-content:space-between;gap:10px;font-size:14px}}
.bar-top small{{color:#64748B;font-weight:600}}
.trilho{{height:10px;background:#F1F5F9;border-radius:99px;margin-top:5px;overflow:hidden}} .cheio{{height:100%;border-radius:99px}}
.alertas{{margin:0;padding-left:20px}} .alertas li{{margin-bottom:8px;line-height:1.45}}
table{{width:100%;border-collapse:collapse;font-size:14px}} td{{padding:9px 6px;border-top:1px solid #E2E8F0;vertical-align:top}}
.dir{{text-align:right;white-space:nowrap}} .cat{{font-size:12px;color:#64748B;margin-top:2px}}
.vazio{{color:#64748B}}
.resumo ul{{margin:0;padding-left:20px;font-size:16px;line-height:1.55}} .resumo li{{margin-bottom:4px}}
.comentario{{border-left:6px solid {dest}}} .comentario p{{margin:0 0 8px;line-height:1.55}} .assina{{font-weight:700;color:{cor}}}
.hist{{margin:-6px 0 10px;color:#475569;font-size:14px}}
footer{{max-width:980px;margin:0 auto;padding:6px 18px 30px;font-size:12px;color:#64748B;line-height:1.5}}
@media (max-width:720px){{.duas{{grid-template-columns:1fr}} h1{{font-size:23px}} .num{{font-size:24px}}}}
@media print{{body{{background:#fff}} section,.card{{box-shadow:none;border:1px solid #E2E8F0}} main{{margin-top:10px}}}}
</style></head><body>
<header><div class="topo">
<p class="bpo">{e(cfg['nome_bpo'])}</p>
<h1>{e(cliente)}</h1>
<p class="periodo">Resultado de {MESES[m - 1]} de {a}{f" (parcial, até {dados['ate']:%d/%m})" if dados.get('parcial') else ""}</p>
</div></header>
<main>
<div class="cards">
<div class="card"><p class="rot">Quanto entrou?</p><p class="num">{reais(dados['entradas'])}</p>{var(dados['var_entradas'], True)}</div>
<div class="card"><p class="rot">Quanto saiu?</p><p class="num">{reais(dados['saidas'])}</p>{var(dados['var_saidas'], False)}</div>
<div class="card res"><p class="rot">{'Sobrou dinheiro? Sim:' if res >= 0 else 'Sobrou dinheiro? Não, faltou:'}</p><p class="num">{reais(abs(res))}</p>{margem}</div>
</div>
<section class="resumo"><h2>O mês em 3 linhas</h2><ul>{frases}</ul></section>
<section><h2>O que eu preciso olhar?</h2><ul class="alertas">{alertas}</ul></section>
{bloco_comentario}
<section><h2>Estou melhor do que antes?</h2>
<p class="hist">{e(historico)}</p>
<div class="legenda"><span><i style="background:{dest}"></i>Entrou</span><span><i style="background:#F59E0B"></i>Saiu</span></div>
{grafico(dados['serie'], dest, '#F59E0B')}</section>
<div class="duas">
<section><h2>Para onde foi o dinheiro?</h2>{barras(dados['cat_desp'], dados['saidas'], '#F59E0B')}</section>
<section><h2>De onde veio o dinheiro?</h2>{barras(dados['cat_rec'], dados['entradas'], dest)}</section>
</div>
<section><h2>Quais foram os maiores pagamentos?</h2><table>{maiores or '<tr><td>Sem pagamentos no mês.</td></tr>'}</table></section>
</main>
<footer>Preparado por {e(cfg['nome_bpo'])}{contato} em {gerado_em:%d/%m/%Y}. Regime de caixa: cada valor está no mês em que foi pago ou recebido.
Transferências entre as contas da própria empresa não entram. Base: {dados['lancamentos']} lançamentos do Conta Azul.</footer>
</body></html>
"""


def gerar(extrato: Path, cliente: str, mes: str | None = None, raiz: Path = RAIZ,
          agora: datetime | None = None) -> tuple[Path, dict]:
    ref = None
    if mes:
        m = re.fullmatch(r"(\d{4})-(\d{2})", mes)
        if not m:
            raise ValueError("o mês vai no formato aaaa-mm, por exemplo 2026-11")
        ref = (int(m.group(1)), int(m.group(2)))
    agora = agora or datetime.now()
    dados = calcular(ler(extrato), ref, agora.date())
    dados["parcial"] = dados["ref"] == (agora.year, agora.month)
    a, mm = dados["ref"]
    # comentário do BPO, escrito por você (ou rascunhado pelo agente e revisado por você)
    arq_com = raiz / "comentarios" / f"{slug(cliente)}-{a}-{mm:02d}.txt"
    comentario = arq_com.read_text(encoding="utf-8") if arq_com.exists() else ""
    pagina = montar(dados, cliente, config_bpo(raiz), agora, comentario)
    pasta = raiz / "saida" / slug(cliente)
    pasta.mkdir(parents=True, exist_ok=True)
    saida = pasta / f"painel-{a}-{mm:02d}.html"
    saida.write_text(pagina, encoding="utf-8")
    return saida, dados


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Dashboard do mês do cliente a partir do extrato do Conta Azul")
    p.add_argument("extrato")
    p.add_argument("--cliente", required=True)
    p.add_argument("--mes", help="aaaa-mm; sem ele, usa o último mês do extrato")
    p.add_argument("--senha", action="store_true", help="gera também a versão trancada, para publicar como link")
    args = p.parse_args(argv)
    try:
        saida, dados = gerar(Path(args.extrato), args.cliente, args.mes)
    except Exception as ex:  # mensagem simples para quem não é técnico
        print(f"PAROU: {ex}")
        return 1
    a, m = dados["ref"]
    print(f"Painel de {MESES[m - 1]}/{a} pronto: {saida}")
    print(f"Entrou {reais(dados['entradas'])} | Saiu {reais(dados['saidas'])} | Resultado {reais(dados['resultado'])}")
    for t in dados["alertas"]:
        print(f"ATENÇÃO: {t}")
    if args.senha:
        from trancar import trancar_cliente
        destino = trancar_cliente(saida, args.cliente)
        print(f"Versão trancada pronta: {destino}")
        print("A senha deste cliente está no arquivo senhas.csv, na pasta do projeto (só no seu computador).")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
