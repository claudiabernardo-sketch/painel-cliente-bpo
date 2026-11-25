"""
Confere o painel sem internet e sem dado real: extrato fictício, conta, alertas,
cadeado e publicação, tudo numa pasta temporária.

    python codigo/testar.py        tem que terminar com "ok"
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import exemplo  # noqa: E402
import painel  # noqa: E402
import publicar  # noqa: E402
import trancar  # noqa: E402
from ler_ca import ArquivoInvalido, ler  # noqa: E402


def main() -> None:
    pasta = Path(tempfile.mkdtemp())
    extrato = exemplo.gerar(pasta / "extrato_financeiro.xls")

    # leitura: .xlsx com nome .xls, transferências marcadas
    lancs = ler(extrato)
    assert sum(x.transferencia for x in lancs) == 24
    assert all(x.valor > 0 for x in lancs)

    # conta do mês: entradas e saídas batem com o extrato, sem as transferências
    dados = painel.calcular(lancs, (2026, 10), date(2026, 12, 5))
    ent = sum((x.valor for x in lancs if not x.transferencia and x.tipo == "Receita"
               and (x.data.year, x.data.month) == (2026, 10)), Decimal(0))
    assert dados["entradas"] == ent and dados["resultado"] == dados["entradas"] - dados["saidas"]
    assert sum(v for _, v in dados["cat_desp"]) == dados["saidas"]
    assert dados["cat_desp"][0][0] == "Fornecedores de insumos"
    assert any("Energia elétrica" in a for a in dados["alertas"]), dados["alertas"]
    assert len(dados["serie"]) == 12

    # mês em andamento: sem --mes, mostra o último mês completo
    assert painel.calcular(lancs, None, date(2026, 10, 20))["ref"] == (2026, 9)
    assert painel.calcular(lancs, None, date(2026, 11, 2))["ref"] == (2026, 10)

    # página: perguntas do cliente, marca do BPO, texto escapado, comentário
    (pasta / "bpo.json").write_text(json.dumps({"nome_bpo": "BPO <Teste>", "cor_principal": "#123456"}), encoding="utf-8")
    (pasta / "comentarios").mkdir()
    (pasta / "comentarios" / "padaria-modelo-2026-10.txt").write_text("Rever a conta de energia.", encoding="utf-8")
    saida, d = painel.gerar(extrato, "Padaria Modelo", "2026-10", raiz=pasta, agora=datetime(2026, 12, 5))
    html = saida.read_text(encoding="utf-8")
    for pergunta in ("Quanto entrou?", "Sobrou dinheiro?", "O que eu preciso olhar?", "Para onde foi o dinheiro?",
                     "Estou melhor do que antes?", "O que o seu BPO recomenda?"):
        assert pergunta in html, pergunta
    assert "BPO &lt;Teste&gt;" in html and "#123456" in html and "Rever a conta de energia." in html
    assert saida.name == "painel-2026-10.html"

    # cadeado: a página trancada não tem os números, e só a senha certa abre
    destino = trancar.trancar_cliente(saida, "Padaria Modelo", raiz=pasta)
    fechado = destino.read_text(encoding="utf-8")
    assert "Quanto entrou?" not in fechado and painel.reais(d["entradas"]) not in fechado
    senha = trancar.senha_do_cliente("padaria-modelo", pasta / "senhas.csv")
    assert senha == trancar.senha_do_cliente("padaria-modelo", pasta / "senhas.csv")  # mesma senha todo mês
    pacote = trancar.cifrar("teste", senha, rodadas=1000)
    assert trancar.decifrar(pacote, senha) == "teste"
    try:
        trancar.decifrar(pacote, "SENHA-ERRADA")
        raise AssertionError("senha errada abriu")
    except Exception as e:
        assert "senha errada" not in str(e)

    # o navegador abre com a mesma conta (Web Crypto), conferido no Node quando ele existir
    try:
        js = ("const P=" + json.dumps(trancar.cifrar(html, senha, rodadas=2000)) + ";"
              "const b=s=>Uint8Array.from(Buffer.from(s,'base64'));(async()=>{const c=globalThis.crypto.subtle;"
              f"const k0=await c.importKey('raw',new TextEncoder().encode('{senha}'),'PBKDF2',false,['deriveKey']);"
              "const k=await c.deriveKey({name:'PBKDF2',salt:b(P.sal),iterations:P.rodadas,hash:'SHA-256'},k0,{name:'AES-GCM',length:256},false,['decrypt']);"
              "const t=new TextDecoder().decode(await c.decrypt({name:'AES-GCM',iv:b(P.iv)},k,b(P.dados)));"
              "console.log(t.includes('Quanto entrou?')?'abriu':'falhou')})()")
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
        assert r.stdout.strip() == "abriu", r.stdout + r.stderr
        navegador = "e no motor do navegador"
    except FileNotFoundError:
        navegador = "(Node não instalado: conferência do navegador pulada)"

    # publicar: só publica o que está trancado, sem configurar o site, para
    try:
        publicar.preparar("Padaria Modelo", raiz=pasta)
        raise AssertionError("publicou sem site configurado")
    except publicar.Recusa:
        pass
    site = pasta / "site"
    site.mkdir()
    (pasta / "bpo.json").write_text(json.dumps({"pasta_paineis": str(site), "url_paineis": "https://exemplo.github.io/paineis"}),
                                    encoding="utf-8")
    _, link = publicar.preparar("Padaria Modelo", raiz=pasta)
    codigo = link.rstrip("/").rsplit("/", 1)[1]
    publicado = (site / codigo / "index.html").read_text(encoding="utf-8")
    assert "padaria" not in link.lower() and publicar.MARCA_TRANCADO in publicado
    assert publicar.preparar("Padaria Modelo", raiz=pasta)[1] == link  # mesmo link todo mês
    destino.write_text(html, encoding="utf-8")  # alguém trocou pela versão aberta
    try:
        publicar.preparar("Padaria Modelo", raiz=pasta)
        raise AssertionError("publicou a versão aberta")
    except publicar.Recusa:
        pass

    # arquivo errado: mensagem clara
    (pasta / "errado.xls").write_bytes(b"isto nao e excel")
    try:
        ler(pasta / "errado.xls")
        raise AssertionError("leu arquivo errado")
    except ArquivoInvalido:
        pass

    print(f"ok: leitura do Conta Azul, transferências, conta do mês, alertas, perguntas, cadeado {navegador}, publicação")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
