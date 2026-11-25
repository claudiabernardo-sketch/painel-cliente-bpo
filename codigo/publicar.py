"""
Publica a versão TRANCADA do painel como link (GitHub Pages).

    python codigo/publicar.py --cliente "Padaria Modelo"

Copia saida/<cliente>/trancado/index.html para a pasta do seu site de painéis
(o "pasta_paineis" do bpo.json), numa pasta com um código aleatório, e envia ao
GitHub. O link fica:  <url_paineis>/<código>/
O código não tem o nome do cliente, e a página só abre com a senha.

Só publica o que está trancado: se a versão trancada não existir, para.
O código de cada cliente fica em links.csv (só no seu computador), e é o mesmo
todo mês: o cliente guarda o link e a senha uma vez só.
"""
from __future__ import annotations

import argparse
import csv
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))

from painel import config_bpo, slug  # noqa: E402

MARCA_TRANCADO = "Este painel é protegido."


class Recusa(Exception):
    pass


def codigo_do_cliente(cliente_slug: str, arquivo: Path) -> str:
    linhas = []
    if arquivo.exists():
        with arquivo.open(encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.DictReader(f, delimiter=";"))
    for x in linhas:
        if x.get("cliente") == cliente_slug and x.get("codigo"):
            return x["codigo"]
    codigo = secrets.token_hex(6)
    linhas.append({"cliente": cliente_slug, "codigo": codigo})
    with arquivo.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cliente", "codigo"], delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    return codigo


def preparar(cliente: str, raiz: Path = RAIZ) -> tuple[Path, str]:
    cfg = config_bpo(raiz)
    pasta_site = Path(str(cfg.get("pasta_paineis") or "")).expanduser()
    url = str(cfg.get("url_paineis") or "").rstrip("/")
    if not cfg.get("pasta_paineis") or not pasta_site.is_dir():
        raise Recusa("falta configurar o site de painéis: veja o passo 6 do COMO-FAZER.md (pasta_paineis no bpo.json)")
    if not url.startswith("https://"):
        raise Recusa("falta o url_paineis no bpo.json, por exemplo https://seu-usuario.github.io/paineis")
    origem = raiz / "saida" / slug(cliente) / "trancado" / "index.html"
    if not origem.exists():
        raise Recusa("não existe a versão trancada deste cliente: gere antes com --senha")
    if MARCA_TRANCADO not in origem.read_text(encoding="utf-8"):
        raise Recusa("o arquivo não parece trancado: nada foi publicado")
    codigo = codigo_do_cliente(slug(cliente), raiz / "links.csv")
    destino = pasta_site / codigo / "index.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origem, destino)
    return pasta_site, f"{url}/{codigo}/"


def enviar(pasta_site: Path, mensagem: str) -> None:
    for cmd in (["git", "add", "-A"], ["git", "commit", "-m", mensagem], ["git", "push"]):
        r = subprocess.run(cmd, cwd=pasta_site, capture_output=True, text=True)
        if r.returncode != 0 and not (cmd[1] == "commit" and "nothing to commit" in (r.stdout + r.stderr)):
            raise Recusa(f"o envio ao GitHub parou em '{' '.join(cmd)}': {(r.stderr or r.stdout).strip()[:300]}")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Publica o painel trancado como link")
    p.add_argument("--cliente", required=True)
    a = p.parse_args(argv)
    try:
        pasta, link = preparar(a.cliente)
        enviar(pasta, "Atualiza painel")
    except Recusa as e:
        print(f"PAROU: {e}")
        return 1
    print(f"PUBLICADO: {link}")
    print("O link abre em 1 ou 2 minutos. Mande o link e a senha por canais diferentes.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
