"""
Tranca o dashboard com senha, para publicar como LINK sem expor os números.

    python codigo/trancar.py saida/<cliente>/painel-<aaaa-mm>.html --cliente "Padaria Modelo"

Como funciona: a página inteira é cifrada (AES-256-GCM, chave derivada da senha
com PBKDF2-SHA256, 310 mil rodadas). O que vai para a internet é só um
formulário de senha e um bloco embaralhado. Sem a senha, ninguém lê os números,
nem quem achar o link. O navegador do cliente abre com a própria senha, sem
servidor no meio.

A senha de cada cliente é criada uma vez e guardada em senhas.csv, na pasta do
projeto, só no seu computador (está no .gitignore). Mande o link e a senha
por canais diferentes: o link por e-mail e a senha pelo WhatsApp, por exemplo.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import html
import os
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SENHAS = RAIZ / "senhas.csv"
RODADAS = 310_000
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sem 0/O, 1/I/L, para ditar sem erro


def nova_senha() -> str:
    return "-".join("".join(secrets.choice(ALFABETO) for _ in range(4)) for _ in range(3))


def chave(senha: str, sal: bytes, rodadas: int = RODADAS) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, rodadas, 32)


def cifrar(conteudo: str, senha: str, rodadas: int = RODADAS) -> dict:
    sal, iv = os.urandom(16), os.urandom(12)
    dados = AESGCM(chave(senha, sal, rodadas)).encrypt(iv, conteudo.encode("utf-8"), None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"sal": b64(sal), "iv": b64(iv), "dados": b64(dados), "rodadas": rodadas}


def decifrar(pacote: dict, senha: str) -> str:
    b = base64.b64decode
    k = chave(senha, b(pacote["sal"]), pacote["rodadas"])
    return AESGCM(k).decrypt(b(pacote["iv"]), b(pacote["dados"]), None).decode("utf-8")


def pagina_trancada(pacote: dict, titulo: str, cor: str = "#0B1B33", dest: str = "#2EA8E6") -> str:
    t = html.escape(titulo)
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{t}</title>
<style>
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:{cor};
font-family:"Segoe UI",Inter,Roboto,Arial,sans-serif;color:#1E293B}}
form{{background:#fff;border-radius:18px;padding:28px 26px;width:min(380px,90vw);box-shadow:0 20px 50px rgba(0,0,0,.25)}}
h1{{margin:0 0 6px;font-size:20px}} p{{margin:0 0 18px;color:#64748B;font-size:14px;line-height:1.5}}
input{{width:100%;box-sizing:border-box;font-size:18px;padding:12px 14px;border:2px solid #CBD5E1;border-radius:10px;letter-spacing:1px}}
button{{margin-top:14px;width:100%;padding:13px;border:0;border-radius:10px;background:{dest};color:#fff;font-size:16px;font-weight:700;cursor:pointer}}
.erro{{color:#B91C1C;font-size:14px;margin:10px 0 0;min-height:18px}}
</style></head><body>
<form id="f"><h1>{t}</h1><p>Este painel é protegido. Digite a senha que você recebeu.</p>
<input id="s" type="password" autocomplete="current-password" placeholder="Senha" autofocus>
<button type="submit">Abrir o painel</button><p class="erro" id="e"></p></form>
<script>
const P={{sal:"{pacote['sal']}",iv:"{pacote['iv']}",dados:"{pacote['dados']}",rodadas:{pacote['rodadas']}}};
const b=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
document.getElementById('f').addEventListener('submit',async ev=>{{
  ev.preventDefault();const er=document.getElementById('e');er.textContent='Abrindo...';
  try{{
    const senha=document.getElementById('s').value.trim().toUpperCase();
    const base=await crypto.subtle.importKey('raw',new TextEncoder().encode(senha),'PBKDF2',false,['deriveKey']);
    const k=await crypto.subtle.deriveKey({{name:'PBKDF2',salt:b(P.sal),iterations:P.rodadas,hash:'SHA-256'}},base,{{name:'AES-GCM',length:256}},false,['decrypt']);
    const txt=new TextDecoder().decode(await crypto.subtle.decrypt({{name:'AES-GCM',iv:b(P.iv)}},k,b(P.dados)));
    document.open();document.write(txt);document.close();
  }}catch(x){{er.textContent='Senha incorreta. Confira e tente de novo.';}}
}});
</script></body></html>
"""


def senha_do_cliente(cliente_slug: str, arquivo: Path = SENHAS) -> str:
    linhas = []
    if arquivo.exists():
        with arquivo.open(encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.DictReader(f, delimiter=";"))
    for x in linhas:
        if x.get("cliente") == cliente_slug and x.get("senha"):
            return x["senha"]
    senha = nova_senha()
    linhas.append({"cliente": cliente_slug, "senha": senha})
    with arquivo.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cliente", "senha"], delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    return senha


def trancar_cliente(painel: Path, cliente: str, raiz: Path = RAIZ) -> Path:
    from painel import config_bpo, slug
    cfg = config_bpo(raiz)
    senha = senha_do_cliente(slug(cliente), raiz / "senhas.csv")
    pacote = cifrar(Path(painel).read_text(encoding="utf-8"), senha)
    destino = Path(painel).parent / "trancado" / "index.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(pagina_trancada(pacote, f"{cliente} · {cfg['nome_bpo']}", cfg["cor_principal"],
                                       cfg["cor_destaque"]), encoding="utf-8")
    return destino


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    p = argparse.ArgumentParser(description="Tranca o painel com a senha do cliente")
    p.add_argument("painel")
    p.add_argument("--cliente", required=True)
    a = p.parse_args()
    print(f"Versão trancada pronta: {trancar_cliente(Path(a.painel), a.cliente)}")
    print("A senha deste cliente está no arquivo senhas.csv, na pasta do projeto.")
