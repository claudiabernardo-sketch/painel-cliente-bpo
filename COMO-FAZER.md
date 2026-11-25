# Como fazer, passo a passo

Para quem nunca fez. Tempo: 10 minutos na primeira vez, 3 minutos por cliente nos meses seguintes.

## 1. Exportar o extrato no Conta Azul

1. No Conta Azul do cliente, abra o **extrato financeiro** (as movimentações das contas).
2. Escolha o período: pegue pelo menos os **últimos 12 meses**. É o que alimenta o gráfico e as comparações.
3. Exporte em **Excel**. O arquivo vem como **extrato_financeiro.xls**.
4. Não abra e salve o arquivo antes de subir: suba do jeito que ele veio.

> Os nomes dos menus do Conta Azul mudam de tempos em tempos. O que importa é o arquivo: o extrato financeiro, em Excel. Se a página disser que faltam colunas, o arquivo exportado não é esse.

## 2. Montar o painel

1. Abra **https://claudiabernardo-sketch.github.io/painel-cliente-bpo/** no Chrome ou no Edge.
2. Arraste o **extrato_financeiro.xls** para a área tracejada.
3. Preencha **o seu BPO** (nome, contato e logo) uma vez só: a página guarda.
4. Preencha **o cliente**: nome, cor principal, cor de destaque e logo. Também fica guardado: no mês seguinte, é só escolher o nome.
5. Confira o **mês** e, se quiser, escreva **o que o seu BPO recomenda**.
6. **Confira a prévia** com o Conta Azul: entradas, saídas e as maiores categorias.

> Logo: PNG ou JPG. A página diminui a imagem sozinha, para o painel ficar leve.

## 3. Entregar como arquivo (o jeito mais simples)

1. Clique em **Baixar o painel**.
2. Mande o arquivo pelo WhatsApp ou por e-mail. O cliente toca no arquivo e abre no navegador do celular.
3. Quer em PDF? Abra o arquivo no computador, **Ctrl + P** (no Mac, **Cmd + P**), **Salvar como PDF**.

## 4. Entregar como link com senha (GitHub Pages, gratuito)

### Só na primeira vez (5 minutos)

1. Crie uma conta gratuita em **github.com**.
2. Clique em **New repository**. Nome: **paineis**. Deixe **Public**, marque **Add README** e clique em **Create repository**.
3. No repositório, abra **Settings** e depois **Pages**. Em **Branch**, escolha **main** e clique em **Save**.
4. Em 1 ou 2 minutos, o endereço aparece no topo da página Pages: **https://seu-usuario.github.io/paineis/**. Copie e cole no campo **Endereço do seu site de painéis**, na página do painel.

### Todo mês, para cada cliente

1. Clique em **Baixar a versão com senha**. Baixa um arquivo com um código no nome, como **k7m2p9xq.html**. Esse código é do cliente e não muda.
2. A página mostra a **senha** do cliente e o **link** dele.
3. No repositório **paineis**, clique em **Add file**, depois **Upload files**, e arraste o arquivo.
4. Clique em **Commit changes**. Em 1 ou 2 minutos, o link abre.
5. Mande o **link** por um caminho (e-mail) e a **senha** por outro (WhatsApp). Na primeira vez só: o cliente guarda os dois, e todo mês você só sobe o arquivo novo, com o mesmo nome.

> Por que com senha: o GitHub Pages é público. A página vai trancada e só abre com a senha. **Nunca publique a versão aberta.**

> O código no nome do arquivo não tem o nome do cliente, de propósito: quem vê a lista de arquivos do seu repositório não sabe de quem é cada painel.

## 5. Com o agente (opcional, para automatizar)

Para quem já usa o Claude (aba Code) ou o ChatGPT (modo Work):

1. Baixe este projeto: no GitHub, botão **Code**, **Download ZIP**. Descompacte numa pasta.
2. Abra a pasta no app, no modo que pede a sua aprovação.
3. Escreva: `configurar o painel do cliente`. O agente instala o Python (se precisar), copia o `bpo.exemplo.json` para `bpo.json` com os dados do seu BPO e roda os testes.
4. Todo mês: ponha o extrato na pasta `extratos/` e escreva `gerar o painel da Padaria Modelo`. Ele monta, mostra os números para você conferir e só publica com o seu ok.

O agente segue as regras do `AGENTS.md`: nunca publica a versão aberta, nunca repete a senha no chat e nunca mexe fora da pasta.
