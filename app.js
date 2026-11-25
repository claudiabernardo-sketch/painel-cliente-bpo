/* Painel do Cliente BPO: a tela. As contas e o painel estão em logica.js. */
(function () {
  'use strict';
  var P = window.Painel;
  var $ = function (id) { return document.getElementById(id); };
  var GUARDA = 'painel-cliente-bpo:v1';
  var estado = { lancs: null, html: '', dados: null };

  // ---------- memória (neste navegador) ----------
  function memoria() { try { return JSON.parse(localStorage.getItem(GUARDA)) || { bpo: {}, clientes: {} }; } catch (e) { return { bpo: {}, clientes: {} }; } }
  function guardar(m) { try { localStorage.setItem(GUARDA, JSON.stringify(m)); } catch (e) { status('Não deu para guardar as logos neste navegador (imagem grande demais). O painel funciona mesmo assim.', true); } }
  function chaveCliente() { return $('cliente').value.trim().toLowerCase(); }
  function codigo() {
    var b = new Uint8Array(8), s = '', a = 'abcdefghjkmnpqrstuvwxyz23456789';
    crypto.getRandomValues(b); for (var i = 0; i < 8; i++) s += a[b[i] % a.length]; return s;
  }
  function doCliente(m, criar) {
    var k = chaveCliente();
    if (!k) return null;
    if (!m.clientes[k] && criar) m.clientes[k] = {};
    return m.clientes[k] || null;
  }
  function salvarCampos() {
    var m = memoria();
    m.bpo.nomeBpo = $('nomeBpo').value; m.bpo.contato = $('contato').value; m.bpo.site = $('site').value;
    var c = doCliente(m, true);
    if (c) { c.nome = $('cliente').value; c.corCliente = $('corCliente').value; c.corDestaque = $('corDestaque').value; }
    guardar(m);
  }
  function carregarBpo() {
    var m = memoria();
    $('nomeBpo').value = m.bpo.nomeBpo || ''; $('contato').value = m.bpo.contato || ''; $('site').value = m.bpo.site || '';
    mostrarLogo('logoBpo', m.bpo.logoBpo);
    var lista = Object.keys(m.clientes).map(function (k) { return m.clientes[k].nome; }).filter(Boolean);
    if (lista.length) {
      var dl = document.createElement('datalist'); dl.id = 'clientes-salvos';
      lista.forEach(function (n) { var o = document.createElement('option'); o.value = n; dl.appendChild(o); });
      document.body.appendChild(dl); $('cliente').setAttribute('list', 'clientes-salvos');
    }
  }
  function carregarCliente() {
    var c = doCliente(memoria(), false);
    if (!c) { mostrarLogo('logoCliente', ''); return; }
    if (c.corCliente) $('corCliente').value = c.corCliente;
    if (c.corDestaque) $('corDestaque').value = c.corDestaque;
    mostrarLogo('logoCliente', c.logoCliente);
  }
  function mostrarLogo(campo, src) {
    var alvo = $('previa-' + campo);
    alvo.innerHTML = src ? '<img alt="" src="' + src + '"><a href="#" data-tirar="' + campo + '">tirar</a>' : '';
  }

  // logo: reduz para no máximo 320 px, para o painel ficar leve
  function lerLogo(arquivo, pronto) {
    var leitor = new FileReader();
    leitor.onload = function () {
      var img = new Image();
      img.onload = function () {
        var escala = Math.min(1, 320 / Math.max(img.width, img.height));
        var cv = document.createElement('canvas');
        cv.width = Math.max(1, Math.round(img.width * escala)); cv.height = Math.max(1, Math.round(img.height * escala));
        cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
        pronto(cv.toDataURL('image/png'));
      };
      img.onerror = function () { status('Não consegui abrir essa imagem. Use PNG ou JPG.', true); };
      img.src = leitor.result;
    };
    leitor.readAsDataURL(arquivo);
  }

  // ---------- leitura do extrato ----------
  function status(msg, erro) { $('status').textContent = msg; $('status').className = 'aviso' + (erro ? ' erro' : ' ok'); }
  function lerBytes(bytes, nome) {
    try {
      var livro = XLSX.read(bytes, { type: 'array', cellDates: true });
      var folha = livro.Sheets[livro.SheetNames[0]];
      var linhas = XLSX.utils.sheet_to_json(folha, { header: 1, raw: true, defval: '', blankrows: false });
      estado.lancs = P.lerLinhas(linhas);
    } catch (e) {
      estado.lancs = null; status(e.message || 'Não consegui ler esse arquivo.', true); atualizar(); return;
    }
    var ms = P.meses(estado.lancs), padrao = P.mesPadrao(estado.lancs, new Date());
    $('mes').innerHTML = ms.slice().reverse().map(function (k) {
      return '<option value="' + k + '"' + (k === padrao ? ' selected' : '') + '>' + P.nomeMes(k) + '</option>';
    }).join('');
    var transf = estado.lancs.filter(function (x) { return x.transferencia; }).length;
    status('Pronto: ' + estado.lancs.length + ' lançamentos de ' + P.nomeMes(ms[0]) + ' a ' + P.nomeMes(ms[ms.length - 1]) +
      (transf ? ' (' + transf + ' transferências entre contas ficam de fora)' : '') + '. Arquivo: ' + nome);
    atualizar();
  }
  function abrirArquivo(arquivo) {
    if (!arquivo) return;
    var leitor = new FileReader();
    leitor.onload = function () { lerBytes(new Uint8Array(leitor.result), arquivo.name); };
    leitor.readAsArrayBuffer(arquivo);
  }

  // ---------- painel ----------
  function config() {
    var m = memoria(), c = doCliente(m, false) || {};
    var ref = +$('mes').value, hoje = new Date();
    var parcial = ref === hoje.getFullYear() * 100 + hoje.getMonth() + 1;
    return {
      cliente: $('cliente').value || 'Cliente', nomeBpo: $('nomeBpo').value, contato: $('contato').value,
      corCliente: $('corCliente').value, corDestaque: $('corDestaque').value,
      logoBpo: m.bpo.logoBpo || '', logoCliente: c.logoCliente || '', comentario: $('comentario').value,
      parcial: parcial, ate: parcial ? 'hoje' : ''
    };
  }
  function atualizar() {
    var ok = !!estado.lancs && !!$('mes').value;
    $('baixar-aberto').disabled = $('baixar-trancado').disabled = !ok;
    if (!ok) {
      $('previa').srcdoc = '<p style="font:16px Segoe UI,Arial,sans-serif;color:#64748B;text-align:center;margin-top:120px">' +
        'Suba o extrato do Conta Azul no passo 1 e o painel aparece aqui.</p>';
      return;
    }
    try {
      estado.dados = P.calcular(estado.lancs, +$('mes').value);
      estado.html = P.montar(estado.dados, config());
      $('previa').srcdoc = estado.html;
    } catch (e) { status(e.message, true); }
  }
  function baixar(nome, conteudo) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([conteudo], { type: 'text/html;charset=utf-8' }));
    a.download = nome; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  function nomeArquivo() {
    var s = ($('cliente').value || 'cliente').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    var k = +$('mes').value;
    return 'painel-' + (s || 'cliente') + '-' + Math.floor(k / 100) + '-' + String(k % 100).padStart(2, '0') + '.html';
  }

  // ---------- eventos ----------
  var zona = $('soltar');
  ['dragenter', 'dragover'].forEach(function (ev) { zona.addEventListener(ev, function (e) { e.preventDefault(); zona.classList.add('em-cima'); }); });
  ['dragleave', 'drop'].forEach(function (ev) { zona.addEventListener(ev, function (e) { e.preventDefault(); zona.classList.remove('em-cima'); }); });
  zona.addEventListener('drop', function (e) { abrirArquivo(e.dataTransfer.files[0]); });
  $('arquivo').addEventListener('change', function () { abrirArquivo(this.files[0]); });
  $('usar-exemplo').addEventListener('click', function (e) {
    e.preventDefault();
    fetch('exemplos/extrato_ficticio_padaria.xls').then(function (r) { if (!r.ok) throw new Error(); return r.arrayBuffer(); })
      .then(function (b) { if (!$('cliente').value) $('cliente').value = 'Padaria Modelo'; carregarCliente(); lerBytes(new Uint8Array(b), 'extrato_ficticio_padaria.xls'); })
      .catch(function () { status('O exemplo só abre pelo link do site (não pelo arquivo no computador). Baixe-o na pasta exemplos/ e arraste aqui.', true); });
  });
  ['nomeBpo', 'contato', 'site'].forEach(function (id) { $(id).addEventListener('input', function () { salvarCampos(); atualizar(); }); });
  ['corCliente', 'corDestaque'].forEach(function (id) { $(id).addEventListener('input', function () { salvarCampos(); atualizar(); }); });
  $('cliente').addEventListener('change', function () { carregarCliente(); salvarCampos(); atualizar(); $('caixa-senha').hidden = true; });
  $('cliente').addEventListener('input', atualizar);
  $('mes').addEventListener('change', atualizar);
  $('comentario').addEventListener('input', atualizar);
  $('logoBpo').addEventListener('change', function () {
    if (!this.files[0]) return;
    lerLogo(this.files[0], function (src) { var m = memoria(); m.bpo.logoBpo = src; guardar(m); mostrarLogo('logoBpo', src); atualizar(); });
  });
  $('logoCliente').addEventListener('change', function () {
    if (!this.files[0]) return;
    if (!chaveCliente()) { status('Escreva primeiro o nome do cliente, depois suba a logo dele.', true); this.value = ''; return; }
    lerLogo(this.files[0], function (src) { var m = memoria(); doCliente(m, true).logoCliente = src; guardar(m); mostrarLogo('logoCliente', src); atualizar(); });
  });
  document.addEventListener('click', function (e) {
    var campo = e.target.getAttribute && e.target.getAttribute('data-tirar');
    if (!campo) return;
    e.preventDefault();
    var m = memoria();
    if (campo === 'logoBpo') delete m.bpo.logoBpo; else { var c = doCliente(m, false); if (c) delete c.logoCliente; }
    guardar(m); mostrarLogo(campo, ''); atualizar();
  });
  $('baixar-aberto').addEventListener('click', function () { if (estado.html) baixar(nomeArquivo(), estado.html); });
  function senhaECodigo(trocar) {
    var m = memoria(), c = doCliente(m, true) || {};
    if (!c.senha || trocar) c.senha = P.novaSenha();
    if (!c.codigo) c.codigo = codigo();
    guardar(m);
    return c;
  }
  function mostrarSenha(c) {
    $('senha').textContent = c.senha;
    var site = ($('site').value || '').trim().replace(/\/+$/, '');
    $('link-cliente').innerHTML = site ? 'Link deste cliente: <b>' + P.esc(site + '/' + c.codigo + '.html') + '</b>' :
      'O link vai ser o endereço do seu site de painéis + <b>/' + c.codigo + '.html</b>';
    $('caixa-senha').hidden = false;
  }
  $('baixar-trancado').addEventListener('click', function () {
    if (!estado.html) return;
    if (!chaveCliente()) { status('Escreva o nome do cliente antes de baixar a versão com senha.', true); return; }
    var c = senhaECodigo(false), botao = this;
    botao.disabled = true; botao.textContent = 'Trancando...';
    P.trancar(estado.html, c.senha, { titulo: $('cliente').value + ' · ' + ($('nomeBpo').value || 'Painel do cliente'), cor: $('corCliente').value, destaque: $('corDestaque').value })
      .then(function (pagina) { baixar(c.codigo + '.html', pagina); mostrarSenha(c); })
      .catch(function () { status('Não consegui trancar neste navegador. Use o Chrome ou o Edge atualizados.', true); })
      .then(function () { botao.disabled = false; botao.textContent = 'Baixar a versão com senha'; });
  });
  $('nova-senha').addEventListener('click', function (e) {
    e.preventDefault();
    if (!confirm('Trocar a senha deste cliente? A senha antiga deixa de abrir o painel quando você publicar o arquivo novo.')) return;
    mostrarSenha(senhaECodigo(true));
  });

  carregarBpo();
  atualizar();
})();
