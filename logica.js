/* Painel do Cliente BPO: lê o extrato financeiro do Conta Azul, faz as contas do mês
   e monta o dashboard com a marca do BPO e do cliente. Sem tela: funciona no navegador
   (window.Painel) e no Node (require), para os testes. Nada sai do computador. */
(function (raiz, fabrica) {
  if (typeof module === 'object' && module.exports) module.exports = fabrica();
  else raiz.Painel = fabrica();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  var CURTO = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  var OBRIGATORIAS = ['Data movimento', 'Tipo', 'Valor (R$)'];
  var COR_SAIDA = '#F59E0B';

  function esc(t) {
    return String(t == null ? '' : t).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function texto(v) { return v == null ? '' : String(v).trim(); }
  function corValida(c, padrao) { return /^#[0-9a-fA-F]{6}$/.test(String(c || '')) ? c : padrao; }
  function imagemValida(src) { return /^data:image\/(png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+$/.test(String(src || '')) ? src : ''; }

  // dinheiro em centavos (inteiros), para a soma nunca errar
  function centavos(v) {
    if (typeof v === 'number') return isFinite(v) ? Math.round(v * 100) : null;
    var s = texto(v).replace('R$', '').trim();
    if (!s) return null;
    if (s.indexOf(',') >= 0) s = s.replace(/\./g, '').replace(',', '.');
    var n = Number(s);
    return isFinite(n) ? Math.round(n * 100) : null;
  }
  function reais(c, sinal) {
    var neg = c < 0, a = Math.abs(c), inteiro = String(Math.floor(a / 100)), cent = String(a % 100);
    if (cent.length < 2) cent = '0' + cent;
    inteiro = inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return (neg ? '- ' : (sinal && c > 0 ? '+ ' : '')) + 'R$ ' + inteiro + ',' + cent;
  }
  function data(v) {
    if (v instanceof Date && !isNaN(v)) return { a: v.getFullYear(), m: v.getMonth() + 1, d: v.getDate() };
    if (typeof v === 'number' && v > 20000 && v < 80000) {  // número de série do Excel
      var dt = new Date(Math.round((v - 25569) * 86400000));
      return { a: dt.getUTCFullYear(), m: dt.getUTCMonth() + 1, d: dt.getUTCDate() };
    }
    var m = /^\s*(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(texto(v));
    if (!m) return null;
    var r = { a: +m[3], m: +m[2], d: +m[1] };
    return (r.m >= 1 && r.m <= 12 && r.d >= 1 && r.d <= 31) ? r : null;
  }
  function chave(a, m) { return a * 100 + m; }
  function anterior(k, n) { var t = Math.floor(k / 100) * 12 + (k % 100 - 1) - (n == null ? 1 : n); return chave(Math.floor(t / 12), t % 12 + 1); }
  function nomeMes(k) { return MESES[k % 100 - 1] + ' de ' + Math.floor(k / 100); }

  // ---------- leitura ----------
  // linhas: lista de listas (a primeira é o cabeçalho), como o SheetJS devolve com header:1
  function lerLinhas(linhas) {
    if (!linhas || !linhas.length) throw new Error('A planilha está vazia.');
    var cab = linhas[0].map(texto);
    var faltam = OBRIGATORIAS.filter(function (c) { return cab.indexOf(c) < 0; });
    if (faltam.length) throw new Error('Este arquivo não é o extrato financeiro do Conta Azul (faltam as colunas ' + faltam.join(', ') + '). No Conta Azul, exporte o extrato financeiro em Excel.');
    var col = {}; cab.forEach(function (n, i) { col[n] = i; });
    var cats = [];
    cab.forEach(function (n, i) {
      var m = /^Categoria (\d+)$/.exec(n);
      if (m && col['Valor na Categoria ' + m[1]] != null) cats.push([+m[1], i, col['Valor na Categoria ' + m[1]]]);
    });
    cats.sort(function (a, b) { return a[0] - b[0]; });
    var saida = [];
    for (var i = 1; i < linhas.length; i++) {
      var l = linhas[i], pega = function (n) { return col[n] == null ? null : l[col[n]]; };
      var d = data(pega('Data movimento')), v = centavos(pega('Valor (R$)')), tipo = texto(pega('Tipo'));
      if (!d || v == null || (tipo !== 'Receita' && tipo !== 'Despesa')) continue;
      var valor = Math.abs(v), lista = [];
      cats.forEach(function (c) {
        var nome = texto(l[c[1]]), vc = centavos(l[c[2]]);
        if (nome && vc != null) lista.push([nome, Math.abs(vc)]);
      });
      if (!lista.length) lista = [['Sem categoria', valor]];
      saida.push({
        k: chave(d.a, d.m), dia: d.d, tipo: tipo, valor: valor, categorias: lista,
        transferencia: texto(pega('Situação')) === 'Transferido' || texto(pega('Origem do lançamento')) === 'Transferência',
        contraparte: texto(pega('Nome do fornecedor/cliente')), descricao: texto(pega('Descrição'))
      });
    }
    if (!saida.length) throw new Error('O arquivo não tem lançamentos de receita ou despesa.');
    return saida;
  }

  // ---------- contas ----------
  function meses(lancs) {
    var s = {};
    lancs.forEach(function (x) { if (!x.transferencia) s[x.k] = true; });
    return Object.keys(s).map(Number).sort(function (a, b) { return a - b; });
  }
  function mesPadrao(lancs, hoje) {
    var ms = meses(lancs), ult = ms[ms.length - 1];
    hoje = hoje || new Date();
    if (ult === chave(hoje.getFullYear(), hoje.getMonth() + 1) && ms.length > 1) return ms[ms.length - 2];
    return ult;
  }
  function somaPor(obj, k, v) { obj[k] = (obj[k] || 0) + v; }
  function ordenar(obj) { return Object.keys(obj).map(function (n) { return [n, obj[n]]; }).sort(function (a, b) { return b[1] - a[1]; }); }

  function calcular(lancs, ref) {
    var validos = lancs.filter(function (x) { return !x.transferencia; });
    var ms = meses(lancs);
    if (!validos.length) throw new Error('O extrato só tem transferências entre contas.');
    if (ms.indexOf(ref) < 0) throw new Error('O extrato não tem lançamentos em ' + nomeMes(ref) + '.');
    var ent = {}, sai = {}, cd = {}, cr = {};
    validos.forEach(function (x) {
      var alvo = x.tipo === 'Receita' ? cr : cd;
      somaPor(x.tipo === 'Receita' ? ent : sai, x.k, x.valor);
      alvo[x.k] = alvo[x.k] || {};
      x.categorias.forEach(function (c) { somaPor(alvo[x.k], c[0], c[1]); });
    });
    var serie = [];
    for (var n = 11; n >= 0; n--) { var k = anterior(ref, n); if (k >= ms[0]) serie.push([k, ent[k] || 0, sai[k] || 0]); }
    var e = ent[ref] || 0, s = sai[ref] || 0, res = e - s, ant = anterior(ref, 1);
    var temAnt = ant in ent || ant in sai;
    var variacao = function (atual, antes) { return antes ? (atual - antes) / antes * 100 : null; };
    var alertas = [];
    if (res < 0) alertas.push('O mês fechou no negativo: saiu ' + reais(-res) + ' a mais do que entrou.');
    ordenar(cd[ref] || {}).forEach(function (par) {
      if (alertas.length >= 4) return;
      var base = [1, 2, 3].map(function (i) { return (cd[anterior(ref, i)] || {})[par[0]] || 0; }).filter(function (v) { return v > 0; });
      if (base.length >= 2) {
        var media = Math.round(base.reduce(function (a, b) { return a + b; }, 0) / base.length);
        if (par[1] > media * 1.25 && par[1] - media >= 30000)
          alertas.push('O gasto com ' + par[0] + ' subiu ' + Math.round((par[1] - media) / media * 100) + '% contra a média dos meses anteriores (' + reais(par[1]) + ' contra ' + reais(media) + ').');
      }
    });
    if (temAnt && ent[ant] && e < ent[ant] * 0.8)
      alertas.push('As entradas caíram ' + Math.round((ent[ant] - e) / ent[ant] * 100) + '% contra o mês anterior.');
    var maiores = validos.filter(function (x) { return x.tipo === 'Despesa' && x.k === ref; })
      .sort(function (a, b) { return b.valor - a.valor; }).slice(0, 5);
    return {
      ref: ref, entradas: e, saidas: s, resultado: res, margem: e ? res / e * 100 : null,
      varEntradas: temAnt ? variacao(e, ent[ant]) : null, varSaidas: temAnt ? variacao(s, sai[ant]) : null,
      ant: temAnt ? ant : null, serie: serie,
      positivos: serie.filter(function (x) { return x[1] - x[2] >= 0; }).length,
      negativos: serie.filter(function (x) { return x[1] - x[2] < 0; }).length,
      catDesp: ordenar(cd[ref] || {}), catRec: ordenar(cr[ref] || {}), maiores: maiores, alertas: alertas,
      lancamentos: validos.filter(function (x) { return x.k === ref; }).length
    };
  }

  function resumo(d) {
    var m = MESES[d.ref % 100 - 1];
    var f = ['Em ' + m + ', entrou ' + reais(d.entradas) + ' e saiu ' + reais(d.saidas) + ': ' +
      (d.resultado >= 0 ? 'sobrou ' + reais(d.resultado) : 'faltou ' + reais(-d.resultado)) + '.'];
    if (d.catDesp.length && d.saidas)
      f.push('O maior gasto foi ' + d.catDesp[0][0] + ': ' + reais(d.catDesp[0][1]) + ', ' + Math.round(d.catDesp[0][1] / d.saidas * 100) + '% de tudo o que saiu.');
    if (d.ant) {
      var p = [];
      if (d.varEntradas != null) p.push('as entradas ' + (d.varEntradas >= 0 ? 'subiram ' : 'caíram ') + Math.abs(Math.round(d.varEntradas)) + '%');
      if (d.varSaidas != null) p.push('as saídas ' + (d.varSaidas >= 0 ? 'subiram ' : 'caíram ') + Math.abs(Math.round(d.varSaidas)) + '%');
      if (p.length) f.push('Comparado a ' + MESES[d.ant % 100 - 1] + ', ' + p.join(' e ') + '.');
    }
    return f;
  }

  // ---------- página ----------
  function grafico(serie, corE) {
    if (!serie.length) return '';
    var L = 900, base = 220, maior = 1, partes = [];
    serie.forEach(function (x) { maior = Math.max(maior, x[1], x[2]); });
    var passo = L / serie.length, barra = Math.min(28, passo / 3);
    serie.forEach(function (x, i) {
      var cx = i * passo + passo / 2;
      [[x[1], corE], [x[2], COR_SAIDA]].forEach(function (b, j) {
        var h = b[0] / maior * (base - 20);
        partes.push('<rect x="' + (cx - barra - 2 + j * (barra + 4)).toFixed(1) + '" y="' + (base - h).toFixed(1) + '" width="' + barra.toFixed(1) +
          '" height="' + h.toFixed(1) + '" rx="4" fill="' + b[1] + '"><title>' + esc(reais(b[0])) + '</title></rect>');
      });
      partes.push('<text x="' + cx.toFixed(1) + '" y="' + (base + 22) + '" text-anchor="middle" font-size="13" fill="#64748B">' +
        CURTO[x[0] % 100 - 1] + '/' + String(Math.floor(x[0] / 100)).slice(2) + '</text>');
    });
    partes.push('<line x1="0" y1="' + base + '" x2="' + L + '" y2="' + base + '" stroke="#E2E8F0" stroke-width="2"/>');
    return '<svg viewBox="0 0 ' + L + ' 260" width="100%" role="img" aria-label="Entradas e saídas dos últimos meses">' + partes.join('') + '</svg>';
  }
  function barras(itens, total, cor) {
    if (!itens.length) return '<p class="vazio">Sem lançamentos no mês.</p>';
    var mostra = itens.slice(0, 7), resto = itens.slice(7).reduce(function (a, b) { return a + b[1]; }, 0);
    if (resto) mostra.push(['Outras', resto]);
    var maior = Math.max.apply(null, mostra.map(function (x) { return x[1]; })) || 1;
    return mostra.map(function (x) {
      var p = total ? Math.round(x[1] / total * 100) : 0;
      return '<div class="bar"><div class="bar-top"><span>' + esc(x[0]) + '</span><b>' + reais(x[1]) + ' <small>' + p + '%</small></b></div>' +
        '<div class="trilho"><div class="cheio" style="width:' + (x[1] / maior * 100).toFixed(1) + '%;background:' + cor + '"></div></div></div>';
    }).join('');
  }

  // cfg: {cliente, nomeBpo, contato, corCliente, corDestaque, logoCliente, logoBpo, comentario, parcial, ate, geradoEm}
  function montar(d, cfg) {
    cfg = cfg || {};
    var cor = corValida(cfg.corCliente, '#0B1B33'), dest = corValida(cfg.corDestaque, '#2EA8E6');
    var logoC = imagemValida(cfg.logoCliente), logoB = imagemValida(cfg.logoBpo);
    var nomeBpo = texto(cfg.nomeBpo) || 'Seu BPO Financeiro', cliente = texto(cfg.cliente) || 'Cliente';
    var res = d.resultado, ref = d.ref, a = Math.floor(ref / 100), m = ref % 100;
    var geradoEm = cfg.geradoEm || new Date();
    var var_ = function (v, bomSeSobe) {
      if (v == null) return '<p class="sub">sem mês anterior para comparar</p>';
      var boa = (v >= 0) === bomSeSobe;
      return '<p class="sub ' + (boa ? 'ok' : 'ruim') + '">' + (v >= 0 ? '+ ' : '- ') + Math.abs(Math.round(v)) + '% contra o mês anterior</p>';
    };
    var nMeses = d.positivos + d.negativos;
    var historico = nMeses > 1 ? 'Nos últimos ' + nMeses + ' meses, sobrou dinheiro em ' + d.positivos + ' e faltou em ' + d.negativos + '.' : '';
    var comentario = texto(cfg.comentario) ? '<section class="comentario"><h2>O que o seu BPO recomenda?</h2>' +
      texto(cfg.comentario).split('\n').filter(function (p) { return p.trim(); }).map(function (p) { return '<p>' + esc(p) + '</p>'; }).join('') +
      '<p class="assina">' + esc(nomeBpo) + '</p></section>' : '';
    var maiores = d.maiores.map(function (x) {
      return '<tr><td>' + (x.dia < 10 ? '0' : '') + x.dia + '/' + (m < 10 ? '0' : '') + m + '</td><td>' + esc(x.contraparte || x.descricao || '-') +
        '<div class="cat">' + esc(x.categorias.map(function (c) { return c[0]; }).join(', ')) + '</div></td><td class="dir">' + reais(x.valor) + '</td></tr>';
    }).join('');
    var dd = function (n) { return (n < 10 ? '0' : '') + n; };
    var periodo = 'Resultado de ' + MESES[m - 1] + ' de ' + a + (cfg.parcial && cfg.ate ? ' (parcial, até ' + cfg.ate + ')' : '');
    var contato = texto(cfg.contato) ? ' · ' + esc(cfg.contato) : '';

    return '<!doctype html>\n<html lang="pt-BR"><head><meta charset="utf-8">\n' +
      '<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="robots" content="noindex, nofollow">\n' +
      '<title>' + esc(cliente) + ' · ' + MESES[m - 1] + ' de ' + a + '</title>\n<style>\n' +
      '*{box-sizing:border-box}body{margin:0;font-family:"Segoe UI",Inter,Roboto,Arial,sans-serif;background:#F1F5F9;color:#1E293B}' +
      'header{background:' + cor + ';color:#fff;padding:24px 22px 34px}.topo{max-width:980px;margin:0 auto;display:flex;align-items:center;gap:18px}' +
      '.logo-c{width:64px;height:64px;border-radius:14px;background:#fff;object-fit:contain;padding:6px;flex:none}' +
      '.bpo{font-size:13px;letter-spacing:2px;text-transform:uppercase;opacity:.85;margin:0}h1{margin:6px 0 4px;font-size:28px}.periodo{margin:0;font-size:16px;opacity:.92}' +
      'main{max-width:980px;margin:-18px auto 0;padding:0 16px 24px}' +
      '.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}' +
      '.card{background:#fff;border-radius:16px;padding:18px 20px;box-shadow:0 6px 18px rgba(15,23,42,.07);border-top:5px solid ' + dest + '}' +
      '.card.res{border-top-color:' + (res >= 0 ? '#16A34A' : '#DC2626') + '}.rot{margin:0;font-size:14px;color:#64748B;font-weight:600}' +
      '.num{margin:6px 0 2px;font-size:28px;font-weight:800}.sub{margin:0;font-size:13px;color:#64748B}.ok{color:#15803D}.ruim{color:#B91C1C}' +
      'section{background:#fff;border-radius:16px;padding:20px;margin-top:16px;box-shadow:0 6px 18px rgba(15,23,42,.05)}h2{margin:0 0 14px;font-size:18px;color:' + cor + '}' +
      '.legenda{display:flex;gap:18px;font-size:13px;color:#475569;margin-bottom:6px}.legenda i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}' +
      '.duas{display:grid;grid-template-columns:1fr 1fr;gap:16px}.bar{margin-bottom:12px}.bar-top{display:flex;justify-content:space-between;gap:10px;font-size:14px}.bar-top small{color:#64748B;font-weight:600}' +
      '.trilho{height:10px;background:#F1F5F9;border-radius:99px;margin-top:5px;overflow:hidden}.cheio{height:100%;border-radius:99px}' +
      '.alertas,.resumo ul{margin:0;padding-left:20px;line-height:1.5}.alertas li,.resumo li{margin-bottom:7px}.resumo ul{font-size:16px}' +
      '.comentario{border-left:6px solid ' + dest + '}.comentario p{margin:0 0 8px;line-height:1.55}.assina{font-weight:700;color:' + cor + '}' +
      '.hist{margin:-6px 0 10px;color:#475569;font-size:14px}table{width:100%;border-collapse:collapse;font-size:14px}td{padding:9px 6px;border-top:1px solid #E2E8F0;vertical-align:top}' +
      '.dir{text-align:right;white-space:nowrap}.cat{font-size:12px;color:#64748B;margin-top:2px}.vazio{color:#64748B}' +
      'footer{max-width:980px;margin:0 auto;padding:4px 18px 30px;font-size:12px;color:#64748B;line-height:1.5;display:flex;gap:14px;align-items:center}' +
      '.logo-b{height:38px;max-width:140px;object-fit:contain;flex:none}' +
      '@media (max-width:720px){.duas{grid-template-columns:1fr}h1{font-size:23px}.num{font-size:24px}.logo-c{width:52px;height:52px}footer{flex-direction:column;align-items:flex-start}}' +
      '@media print{body{background:#fff}section,.card{box-shadow:none;border:1px solid #E2E8F0}}\n</style></head><body>\n' +
      '<header><div class="topo">' + (logoC ? '<img class="logo-c" src="' + logoC + '" alt="Logo ' + esc(cliente) + '">' : '') +
      '<div><p class="bpo">' + esc(nomeBpo) + '</p><h1>' + esc(cliente) + '</h1><p class="periodo">' + esc(periodo) + '</p></div></div></header>\n<main>\n' +
      '<div class="cards">' +
      '<div class="card"><p class="rot">Quanto entrou?</p><p class="num">' + reais(d.entradas) + '</p>' + var_(d.varEntradas, true) + '</div>' +
      '<div class="card"><p class="rot">Quanto saiu?</p><p class="num">' + reais(d.saidas) + '</p>' + var_(d.varSaidas, false) + '</div>' +
      '<div class="card res"><p class="rot">' + (res >= 0 ? 'Sobrou dinheiro? Sim:' : 'Sobrou dinheiro? Não, faltou:') + '</p><p class="num">' + reais(Math.abs(res)) + '</p>' +
      (d.margem == null ? '' : '<p class="sub">' + Math.round(d.margem) + '% do que entrou</p>') + '</div></div>\n' +
      '<section class="resumo"><h2>O mês em 3 linhas</h2><ul>' + resumo(d).map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('') + '</ul></section>\n' +
      '<section><h2>O que eu preciso olhar?</h2><ul class="alertas">' + (d.alertas.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') || '<li>Nenhum alerta neste mês.</li>') + '</ul></section>\n' +
      comentario +
      '<section><h2>Estou melhor do que antes?</h2><p class="hist">' + esc(historico) + '</p>' +
      '<div class="legenda"><span><i style="background:' + dest + '"></i>Entrou</span><span><i style="background:' + COR_SAIDA + '"></i>Saiu</span></div>' + grafico(d.serie, dest) + '</section>\n' +
      '<div class="duas"><section><h2>Para onde foi o dinheiro?</h2>' + barras(d.catDesp, d.saidas, COR_SAIDA) + '</section>' +
      '<section><h2>De onde veio o dinheiro?</h2>' + barras(d.catRec, d.entradas, dest) + '</section></div>\n' +
      '<section><h2>Quais foram os maiores pagamentos?</h2><table>' + (maiores || '<tr><td>Sem pagamentos no mês.</td></tr>') + '</table></section>\n</main>\n' +
      '<footer>' + (logoB ? '<img class="logo-b" src="' + logoB + '" alt="Logo ' + esc(nomeBpo) + '">' : '') +
      '<span>Preparado por ' + esc(nomeBpo) + contato + ' em ' + dd(geradoEm.getDate()) + '/' + dd(geradoEm.getMonth() + 1) + '/' + geradoEm.getFullYear() +
      '. Regime de caixa: cada valor está no mês em que foi pago ou recebido. Transferências entre as contas da própria empresa não entram. Base: ' +
      d.lancamentos + ' lançamentos do Conta Azul.</span></footer>\n</body></html>\n';
  }

  // ---------- cadeado (senha) ----------
  var ALFABETO = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
  function novaSenha(cripto) {
    var c = cripto || (typeof crypto !== 'undefined' ? crypto : null), bytes = new Uint8Array(12), s = '';
    c.getRandomValues(bytes);
    for (var i = 0; i < 12; i++) { s += ALFABETO[bytes[i] % ALFABETO.length]; if (i === 3 || i === 7) s += '-'; }
    return s;
  }
  function b64(bytes) {
    if (typeof Buffer !== 'undefined') return Buffer.from(bytes).toString('base64');
    var s = ''; for (var i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]); return btoa(s);
  }
  function cifrar(conteudo, senha, rodadas, cripto) {
    var c = cripto || crypto, sal = new Uint8Array(16), iv = new Uint8Array(12);
    rodadas = rodadas || 310000;
    c.getRandomValues(sal); c.getRandomValues(iv);
    return c.subtle.importKey('raw', new TextEncoder().encode(String(senha).trim().toUpperCase()), 'PBKDF2', false, ['deriveKey'])
      .then(function (base) {
        return c.subtle.deriveKey({ name: 'PBKDF2', salt: sal, iterations: rodadas, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['encrypt']);
      })
      .then(function (k) { return c.subtle.encrypt({ name: 'AES-GCM', iv: iv }, k, new TextEncoder().encode(conteudo)); })
      .then(function (dados) { return { sal: b64(sal), iv: b64(iv), dados: b64(new Uint8Array(dados)), rodadas: rodadas }; });
  }
  var MARCA_TRANCADO = 'Este painel é protegido.';
  function paginaTrancada(p, titulo, cor, dest) {
    cor = corValida(cor, '#0B1B33'); dest = corValida(dest, '#2EA8E6');
    return '<!doctype html>\n<html lang="pt-BR"><head><meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n' +
      '<meta name="robots" content="noindex, nofollow">\n<title>' + esc(titulo) + '</title>\n<style>' +
      'body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:' + cor + ';font-family:"Segoe UI",Inter,Roboto,Arial,sans-serif;color:#1E293B}' +
      'form{background:#fff;border-radius:18px;padding:28px 26px;width:min(380px,90vw);box-shadow:0 20px 50px rgba(0,0,0,.25)}' +
      'h1{margin:0 0 6px;font-size:20px}p{margin:0 0 18px;color:#64748B;font-size:14px;line-height:1.5}' +
      'input{width:100%;box-sizing:border-box;font-size:18px;padding:12px 14px;border:2px solid #CBD5E1;border-radius:10px;letter-spacing:1px}' +
      'button{margin-top:14px;width:100%;padding:13px;border:0;border-radius:10px;background:' + dest + ';color:#fff;font-size:16px;font-weight:700;cursor:pointer}' +
      '.erro{color:#B91C1C;font-size:14px;margin:10px 0 0;min-height:18px}</style></head><body>\n' +
      '<form id="f"><h1>' + esc(titulo) + '</h1><p>' + MARCA_TRANCADO + ' Digite a senha que você recebeu.</p>' +
      '<input id="s" type="password" autocomplete="current-password" placeholder="Senha" autofocus>' +
      '<button type="submit">Abrir o painel</button><p class="erro" id="e"></p></form>\n<script>\n' +
      'const P=' + JSON.stringify(p) + ';\nconst b=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));\n' +
      'document.getElementById("f").addEventListener("submit",async ev=>{ev.preventDefault();const er=document.getElementById("e");er.textContent="Abrindo...";\n' +
      'try{const senha=document.getElementById("s").value.trim().toUpperCase();\n' +
      'const base=await crypto.subtle.importKey("raw",new TextEncoder().encode(senha),"PBKDF2",false,["deriveKey"]);\n' +
      'const k=await crypto.subtle.deriveKey({name:"PBKDF2",salt:b(P.sal),iterations:P.rodadas,hash:"SHA-256"},base,{name:"AES-GCM",length:256},false,["decrypt"]);\n' +
      'const txt=new TextDecoder().decode(await crypto.subtle.decrypt({name:"AES-GCM",iv:b(P.iv)},k,b(P.dados)));\n' +
      'document.open();document.write(txt);document.close();}catch(x){er.textContent="Senha incorreta. Confira e tente de novo.";}});\n</script></body></html>\n';
  }
  function trancar(html, senha, opcoes, cripto) {
    opcoes = opcoes || {};
    return cifrar(html, senha, opcoes.rodadas, cripto).then(function (p) {
      return paginaTrancada(p, opcoes.titulo || 'Painel do cliente', opcoes.cor, opcoes.destaque);
    });
  }

  return {
    MESES: MESES, lerLinhas: lerLinhas, meses: meses, mesPadrao: mesPadrao, calcular: calcular, resumo: resumo,
    montar: montar, reais: reais, nomeMes: nomeMes, novaSenha: novaSenha, cifrar: cifrar, trancar: trancar,
    MARCA_TRANCADO: MARCA_TRANCADO, esc: esc
  };
});
