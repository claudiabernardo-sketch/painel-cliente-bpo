# Painel do Cliente BPO: regras para o agente

Este projeto monta o dashboard do mês do cliente a partir do extrato financeiro do Conta Azul e entrega como arquivo ou como link com senha. Os números são de clientes reais: na dúvida, pare e pergunte.

## Quem é a pessoa

Dona ou operadora de BPO Financeiro, **não técnica**. Fale em português do Brasil, simples, uma coisa por vez. Comando que a pessoa precisa rodar: dê pronto para copiar e diga onde colar.

## Por onde começar

- Se não existe `bpo.json`, ou se a pessoa disser "configurar o painel do cliente": siga **Configurar**, abaixo.
- Pedido de painel ("gerar o painel da Padaria Modelo", "painel de outubro"): siga o skill `painel-cliente` (`.agents/skills/painel-cliente/SKILL.md`).

## Configurar

1. Confira o Python (`python --version`, 3.10 ou mais novo). Sem Python, guie a instalação pelo python.org.
2. `python -m pip install -r requirements.txt`
3. Copie `bpo.exemplo.json` para `bpo.json` e preencha com a pessoa: nome do BPO, contato e cores. `pasta_paineis` e `url_paineis` só quando ela quiser publicar link (passo 4 do COMO-FAZER.md).
4. `python codigo/testar.py` tem que terminar com `ok`.

## Regras que não mudam

1. **Nunca publique a versão aberta.** Link só com a versão trancada (`--senha`), e só pelo `codigo/publicar.py`, que confere o cadeado.
2. **Publicar só com o ok explícito da pessoa, nesta conversa, para aquele cliente e aquele mês**, depois de mostrar os totais (entrou, saiu, resultado) para ela conferir com o Conta Azul.
3. **Nunca leia, mostre nem repita no chat o conteúdo de `senhas.csv`.** A pessoa abre o arquivo e pega a senha. Diga que ela mande o link e a senha por caminhos diferentes.
4. **Nunca mande nada ao cliente.** Quem manda o arquivo, o link e a senha é a pessoa.
5. **Não invente número.** Os valores vêm só do extrato, pelos comandos de `codigo/`. Não reescreva as contas na conversa.
6. **Dados de cliente ficam fora do Git:** `extratos/`, `saida/`, `comentarios/`, `senhas.csv`, `links.csv` e `bpo.json` estão no `.gitignore`. Não mude isso.
7. **Fique dentro da pasta do projeto**, com uma exceção: a `pasta_paineis` do `bpo.json`, e só pelo `codigo/publicar.py`.
8. Se mudar algo em `codigo/` ou em `logica.js`, rode antes e depois `python codigo/testar.py` e `node testes/testar_pagina.js`. Os dois têm que terminar com `ok`.

## Comandos

Rode da raiz do projeto.

```
python codigo/painel.py extratos/<arquivo>.xls --cliente "Nome do cliente" [--mes aaaa-mm] [--senha]
python codigo/trancar.py saida/<cliente>/painel-<aaaa-mm>.html --cliente "Nome do cliente"
python codigo/publicar.py --cliente "Nome do cliente"
python codigo/exemplo.py          extrato fictício para treinar
python codigo/testar.py           testes (sem internet, sem dado real)
```

O comentário do BPO no painel vem de `comentarios/<cliente>-<aaaa>-<mm>.txt`. Você pode rascunhar com base nos alertas, mas a pessoa revisa e aprova o texto antes de gerar.
