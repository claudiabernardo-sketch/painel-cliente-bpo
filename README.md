# Painel do Cliente BPO

**Por Cláudia Bernardo.** O dashboard do mês do cliente, a partir do extrato financeiro do Conta Azul, com a logo e as cores do seu BPO e do cliente.

**Abra e use, sem instalar:** https://claudiabernardo-sketch.github.io/painel-cliente-bpo/

O painel responde as perguntas que o cliente sempre faz:

- Quanto entrou? Quanto saiu? Sobrou dinheiro?
- O que eu preciso olhar? (alertas automáticos: mês no negativo, gasto que subiu, entrada que caiu)
- Estou melhor do que antes? (os últimos 12 meses)
- Para onde foi o dinheiro? De onde veio?
- Quais foram os maiores pagamentos?
- O que o meu BPO recomenda? (um comentário seu, opcional)

Veja um exemplo pronto, com dados fictícios: [exemplos/painel_exemplo_padaria.html](https://claudiabernardo-sketch.github.io/painel-cliente-bpo/exemplos/painel_exemplo_padaria.html)

## Como funciona

1. **Suba o extrato** financeiro do Conta Azul (o arquivo `extrato_financeiro.xls`).
2. **Personalize:** nome e logo do seu BPO, nome, logo e cores do cliente, e o seu comentário.
3. **Confira** a prévia.
4. **Entregue** de um dos dois jeitos:
   - **Como arquivo:** baixe e mande pelo WhatsApp ou por e-mail. Nada vai para a internet.
   - **Como link com senha:** baixe a versão trancada e publique no GitHub Pages (gratuito). Sem a senha, ninguém vê os números, nem quem achar o link.

O passo a passo completo, para quem nunca fez, está no [COMO-FAZER.md](COMO-FAZER.md) e na própria página.

## Segurança, com honestidade

- **O extrato é lido no seu navegador** e não é enviado a lugar nenhum. Não há servidor, conta nem IA no meio.
- **A versão com senha é cifrada** (AES-256-GCM, chave derivada da senha com PBKDF2-SHA256, 310 mil rodadas). O que vai para a internet é um bloco embaralhado e um campo de senha.
- **A força está na senha:** use a que a página gera (12 letras e números) e mande o link e a senha por caminhos diferentes.
- **Nunca publique a versão aberta** (o "Baixar o painel"): ela é para mandar como arquivo.
- As contas seguem o **regime de caixa** (o mês em que foi pago ou recebido) e deixam de fora as transferências entre contas da própria empresa. Confira com o Conta Azul antes de mandar: o painel é do seu BPO.

## Para automatizar com o agente

A pasta `codigo/` tem a mesma conta em Python, para o Claude (aba Code) ou o ChatGPT (modo Work) gerarem e publicarem os painéis todo mês, com o seu ok. As regras estão no `AGENTS.md`. Veja a seção "Com o agente" do [COMO-FAZER.md](COMO-FAZER.md).

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `index.html`, `app.js`, `estilo.css` | A página: subir o extrato, personalizar, conferir e entregar |
| `logica.js` | As contas, o painel e o cadeado (a mesma lógica no navegador e nos testes) |
| `exemplos/` | Extrato e painel fictícios da Padaria Modelo, para treinar |
| `codigo/` | A versão em Python, para o agente |
| `testes/` | Os testes da página (`node testes/testar_pagina.js`) |
| `AGENTS.md`, `CLAUDE.md`, `.agents/skills/` | As regras e o procedimento do agente |

## Licença

PolyForm Shield 1.0.0 (ver `LICENSE`): você pode usar no seu BPO, com os seus clientes, à vontade. Não pode usar para criar ou vender um produto que concorra com este.
