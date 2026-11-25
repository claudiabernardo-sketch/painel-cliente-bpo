---
name: painel-cliente
description: Gera o dashboard do mês do cliente a partir do extrato financeiro do Conta Azul, mostra os números para conferência e, com o ok da pessoa, tranca com senha e publica o link. Use quando a pessoa disser "gerar o painel", "painel do cliente", "painel de outubro", "publicar o painel", "dashboard do cliente". Não use antes de existir o bpo.json (ver AGENTS.md, Configurar).
---

# Painel do cliente, todo mês

Antes de tudo: leia o `AGENTS.md` e o `bpo.json`.

## 1. Achar o extrato

1. Procure em `extratos/` o extrato do cliente pedido. Se houver mais de um, pergunte qual.
2. Sem extrato: peça para a pessoa exportar o extrato financeiro do Conta Azul em Excel (últimos 12 meses) e salvar em `extratos/`. Explique com o passo 1 do `COMO-FAZER.md`.

## 2. Gerar e mostrar para conferência

1. `python codigo/painel.py extratos/<arquivo> --cliente "<nome>"` (com `--mes aaaa-mm` se ela pediu um mês).
2. Mostre o resumo da saída: mês, entrou, saiu, resultado e os alertas. Peça para ela conferir com o Conta Azul.
3. Pergunte se ela quer um comentário do BPO. Se quiser, proponha um rascunho curto (2 ou 3 frases) a partir dos alertas, ajuste com ela, salve em `comentarios/<cliente>-<aaaa>-<mm>.txt` e gere de novo.
4. Diga onde ficou o arquivo (`saida/<cliente>/painel-<aaaa-mm>.html`) e que ela pode abrir com dois cliques para ver.

## 3. Entregar

Pergunte: **como arquivo** ou **como link com senha**?

- **Arquivo:** pronto. Ela manda o `painel-<aaaa-mm>.html` pelo WhatsApp ou por e-mail.
- **Link:** só com o ok dela para aquele cliente e aquele mês.
  1. `python codigo/painel.py extratos/<arquivo> --cliente "<nome>" --senha`
  2. `python codigo/publicar.py --cliente "<nome>"` (sem `pasta_paineis` no `bpo.json`, guie o passo 4 do `COMO-FAZER.md` antes).
  3. Mostre o link. Diga que a senha está em `senhas.csv` (não leia nem repita a senha) e que ela mande o link e a senha por caminhos diferentes.

Feche com uma linha: cliente, mês, resultado e como foi entregue.
