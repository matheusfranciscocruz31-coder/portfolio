// UI Enhancements, Parallax, Filters and Automation Lab (XML -> Excel)
(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // Parallax layers
  const layers = $$('.layer');
  const onScroll = () => {
    const y = window.scrollY || window.pageYOffset;
    layers.forEach((el) => {
      const speed = parseFloat(el.dataset.speed || '0.04');
      el.style.transform = `translate3d(0, ${y * speed}px, 0)`;
    });
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  // Reveal on scroll
  const revealTargets = [
    '.section',
    '.card',
    '.stat',
    '.hero h1',
    '.subtitle',
    '.cta',
  ].flatMap((sel) => $$(sel));
  revealTargets.forEach((el) => el.classList.add('reveal'));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add('show');
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.15 });
  revealTargets.forEach((el) => io.observe(el));

  // Navbar shadow state on scroll
  const navbar = $('.navbar');
  const navScroll = () => {
    navbar.style.boxShadow = window.scrollY > 8 ? 'var(--shadow)' : 'none';
  };
  navScroll();
  window.addEventListener('scroll', navScroll, { passive: true });

  // Counter animation
  const counters = $$('.num[data-count]');
  const animateCounter = (el) => {
    const target = Number(el.dataset.count || '0');
    const duration = 1200;
    const start = performance.now();
    const tick = (t) => {
      const p = Math.min(1, (t - start) / duration);
      const val = Math.floor(target * (0.2 + 0.8 * Math.pow(p, 0.8)));
      el.textContent = val.toString();
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  const countersIO = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        animateCounter(e.target);
        countersIO.unobserve(e.target);
      }
    });
  }, { threshold: 0.6 });
  counters.forEach((el) => countersIO.observe(el));

  // Project filters
  const filterButtons = $$('.filter');
  const projects = $$('.project');
  filterButtons.forEach((btn) => btn.addEventListener('click', () => {
    filterButtons.forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    const tag = btn.dataset.filter;
    projects.forEach((card) => {
      const tags = (card.dataset.tags || '').split(/\s+/);
      const show = tag === 'all' || tags.includes(tag);
      card.style.display = show ? '' : 'none';
    });
  }));

  // Automation Lab (XML -> Excel)
  const fileInput = $('#fileInput');
  const dropzone = $('#dropzone');
  const btnExemplo = $('#btnExemplo');
  const btnProcessar = $('#btnProcessar');
  const btnBaixar = $('#btnBaixar');
  const status = $('#labStatus');
  const preview = $('#preview');

  let parsedNota = null;
  let workbookBundle = null;

  const setStatus = (msg, type = 'info') => {
    status.textContent = msg;
    status.style.color = type === 'error' ? '#fca5a5' : (type === 'ok' ? '#86efac' : '');
  };

  const formatCurrency = (value) => {
    const n = typeof value === 'number' && Number.isFinite(value) ? value : Number(value) || 0;
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n);
  };

  const formatNumber = (value, decimals = 2) => {
    const n = typeof value === 'number' && Number.isFinite(value) ? value : Number(value) || 0;
    return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(n);
  };

  const escapeHtml = (value) => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  const childByLocalName = (parent, local) => {
    if (!parent) return null;
    return Array.from(parent.children).find((node) => node.localName === local) || null;
  };

  const textPath = (parent, path) => {
    let node = parent;
    for (const name of path) {
      node = childByLocalName(node, name);
      if (!node) return '';
    }
    return node.textContent ? node.textContent.trim() : '';
  };

  const decodeFormaPagamento = (codigo) => {
    const map = {
      '01': 'Dinheiro',
      '02': 'Cheque',
      '03': 'Cartão de Crédito',
      '04': 'Cartão de Débito',
      '05': 'Crédito Loja',
      '10': 'Vale Alimentação',
      '11': 'Vale Refeição',
      '12': 'Vale Presente',
      '13': 'Vale Combustível',
      '14': 'Duplicata',
      '15': 'Boleto',
      '16': 'Depósito bancário',
      '17': 'Pagamento Instantâneo (PIX)',
      '18': 'Transferência bancária',
      '19': 'Carteira Digital',
      '99': 'Outros',
    };
    return map[codigo] || codigo || 'Não informado';
  };

  const parseNotaFiscal = (xmlText) => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlText, 'application/xml');
    if (doc.querySelector('parsererror')) {
      throw new Error('XML inválido.');
    }

    const infNFe = doc.getElementsByTagName('infNFe')[0] || doc.getElementsByTagNameNS('*', 'infNFe')[0];
    if (!infNFe) {
      throw new Error('Estrutura infNFe não encontrada.');
    }

    const ide = childByLocalName(infNFe, 'ide');
    const emit = childByLocalName(infNFe, 'emit');
    const dest = childByLocalName(infNFe, 'dest');
    const totalNode = childByLocalName(childByLocalName(infNFe, 'total'), 'ICMSTot');
    const pag = childByLocalName(infNFe, 'pag');

    const numero = textPath(ide, ['nNF']);
    const serie = textPath(ide, ['serie']);
    const chave = (infNFe.getAttribute('Id') || '').replace(/^NFe/i, '');
    const emissorNome = textPath(emit, ['xNome']);
    const emissorDoc = textPath(emit, ['CNPJ']) || textPath(emit, ['CPF']);
    const destNome = textPath(dest, ['xNome']);
    const destDoc = textPath(dest, ['CNPJ']) || textPath(dest, ['CPF']);
    const dataEmissaoRaw = textPath(ide, ['dhEmi']) || textPath(ide, ['dEmi']);
    const dataEmissao = dataEmissaoRaw ? new Date(dataEmissaoRaw).toLocaleString('pt-BR') : '';

    const valorTotal = Number(textPath(totalNode, ['vNF']) || 0);
    const icmsTotal = Number(textPath(totalNode, ['vICMS']) || 0);

    const itens = Array.from(infNFe.children)
      .filter((node) => node.localName === 'det')
      .map((det) => {
        const prod = childByLocalName(det, 'prod');
        const imposto = childByLocalName(det, 'imposto');
        return {
          numero: det.getAttribute('nItem') || '',
          codigo: textPath(prod, ['cProd']),
          descricao: textPath(prod, ['xProd']),
          cfop: textPath(prod, ['CFOP']),
          ncm: textPath(prod, ['NCM']),
          unidade: textPath(prod, ['uCom']),
          quantidade: Number(textPath(prod, ['qCom']) || 0),
          valorUnitario: Number(textPath(prod, ['vUnCom']) || 0),
          valorTotal: Number(textPath(prod, ['vProd']) || 0),
          icms: Number(textPath(imposto, ['ICMS', 'ICMS00', 'vICMS']) || textPath(imposto, ['ICMS', 'vICMS']) || 0),
          ipi: Number(textPath(imposto, ['IPI', 'IPITrib', 'vIPI']) || 0),
        };
      });

    const pagamentos = pag
      ? Array.from(pag.children)
        .filter((node) => node.localName === 'detPag')
        .map((detPag) => ({
          forma: decodeFormaPagamento(textPath(detPag, ['tPag'])),
          valor: Number(textPath(detPag, ['vPag']) || 0),
        }))
      : [];

    return {
      chave,
      numero,
      serie,
      dataEmissao,
      emissor: { nome: emissorNome, documento: emissorDoc },
      destinatario: { nome: destNome, documento: destDoc },
      valorTotal,
      icmsTotal,
      itens,
      pagamentos,
    };
  };

  const tableHtml = (rows, columns, emptyMessage) => {
    if (!rows.length) {
      return `<p class="muted">${escapeHtml(emptyMessage)}</p>`;
    }
    let html = '<table><thead><tr>';
    html += columns.map((col) => `<th>${escapeHtml(col.label)}</th>`).join('');
    html += '</tr></thead><tbody>';
    html += rows.map((row) => `<tr>${columns.map((col) => `<td>${escapeHtml(row[col.key] ?? '')}</td>`).join('')}</tr>`).join('');
    html += '</tbody></table>';
    return html;
  };

  const renderPreview = (nota) => {
    if (!nota) {
      preview.innerHTML = '<p class="muted">Envie um XML de NF-e para visualizar o resumo aqui.</p>';
      return;
    }

    const resumoRows = [
      { campo: 'Chave de acesso', valor: nota.chave || '—' },
      { campo: 'Número / Série', valor: `${nota.numero || '—'} / ${nota.serie || '—'}` },
      { campo: 'Data de emissão', valor: nota.dataEmissao || '—' },
      { campo: 'Emitente', valor: `${nota.emissor.nome || '—'} (${nota.emissor.documento || '—'})` },
      { campo: 'Destinatário', valor: `${nota.destinatario.nome || '—'} (${nota.destinatario.documento || '—'})` },
      { campo: 'Valor total', valor: formatCurrency(nota.valorTotal) },
      { campo: 'ICMS total', valor: formatCurrency(nota.icmsTotal) },
      { campo: 'Itens na nota', valor: formatNumber(nota.itens.length, 0) },
    ];

    const itensPreview = nota.itens.slice(0, 12).map((item) => ({
      numero: item.numero,
      descricao: item.descricao,
      quantidade: formatNumber(item.quantidade, 2),
      unitario: formatCurrency(item.valorUnitario),
      total: formatCurrency(item.valorTotal),
    }));

    const pagamentosPreview = nota.pagamentos.map((pagamento) => ({
      forma: pagamento.forma,
      valor: formatCurrency(pagamento.valor),
    }));

    const itensTitle = nota.itens.length > 12
      ? `Itens (mostrando 12 de ${nota.itens.length})`
      : 'Itens';

    preview.classList.remove('skeleton');
    preview.innerHTML = `
      <div class="preview-section">
        <h4>Resumo</h4>
        ${tableHtml(resumoRows, [
          { key: 'campo', label: 'Campo' },
          { key: 'valor', label: 'Valor' },
        ], 'Sem dados de resumo.')}
      </div>
      <div class="preview-section">
        <h4>${escapeHtml(itensTitle)}</h4>
        ${tableHtml(itensPreview, [
          { key: 'numero', label: 'Item' },
          { key: 'descricao', label: 'Descrição' },
          { key: 'quantidade', label: 'Qtd.' },
          { key: 'unitario', label: 'Vlr. unitário' },
          { key: 'total', label: 'Vlr. total' },
        ], 'Sem itens para exibir.')}
      </div>
      <div class="preview-section">
        <h4>Pagamentos</h4>
        ${tableHtml(pagamentosPreview, [
          { key: 'forma', label: 'Forma' },
          { key: 'valor', label: 'Valor' },
        ], 'Sem pagamentos informados.')}
      </div>
    `;
  };

  const buildWorkbook = (nota) => {
    const wb = XLSX.utils.book_new();

    const resumoData = [
      { Campo: 'Chave de acesso', Valor: nota.chave || '' },
      { Campo: 'Número', Valor: nota.numero || '' },
      { Campo: 'Série', Valor: nota.serie || '' },
      { Campo: 'Data de emissão', Valor: nota.dataEmissao || '' },
      { Campo: 'Emitente', Valor: `${nota.emissor.nome || ''} (${nota.emissor.documento || ''})` },
      { Campo: 'Destinatário', Valor: `${nota.destinatario.nome || ''} (${nota.destinatario.documento || ''})` },
      { Campo: 'Valor total', Valor: nota.valorTotal },
      { Campo: 'ICMS total', Valor: nota.icmsTotal },
      { Campo: 'Quantidade de itens', Valor: nota.itens.length },
    ];
    const resumoSheet = XLSX.utils.json_to_sheet(resumoData);
    XLSX.utils.book_append_sheet(wb, resumoSheet, 'Resumo');

    const itensSheet = XLSX.utils.json_to_sheet(nota.itens.map((item) => ({
      Item: item.numero,
      Código: item.codigo,
      Descrição: item.descricao,
      CFOP: item.cfop,
      NCM: item.ncm,
      Unidade: item.unidade,
      Quantidade: item.quantidade,
      ValorUnitario: item.valorUnitario,
      ValorTotal: item.valorTotal,
      ICMS: item.icms,
      IPI: item.ipi,
    })));
    XLSX.utils.book_append_sheet(wb, itensSheet, 'Itens');

    const pagamentosSheet = XLSX.utils.json_to_sheet(nota.pagamentos.map((pagamento) => ({
      Forma: pagamento.forma,
      Valor: pagamento.valor,
    })));
    XLSX.utils.book_append_sheet(wb, pagamentosSheet, 'Pagamentos');

    return wb;
  };

  const resetLab = () => {
    parsedNota = null;
    workbookBundle = null;
    btnProcessar.disabled = true;
    btnBaixar.disabled = true;
    preview.classList.add('skeleton');
    preview.innerHTML = '';
  };

  const handleFile = async (file) => {
    resetLab();
    setStatus(`Lendo arquivo: ${file.name}…`);
    try {
      const xmlText = await file.text();
      parsedNota = parseNotaFiscal(xmlText);
      renderPreview(parsedNota);
      setStatus('XML pronto para gerar planilha.');
      btnProcessar.disabled = false;
    } catch (err) {
      console.error(err);
      setStatus('Não consegui interpretar o XML. Confirme se é NF-e (versão 4.0).', 'error');
    }
  };

  // Dropzone interactions
  if (dropzone) {
    ['dragenter', 'dragover'].forEach((eName) => dropzone.addEventListener(eName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.style.background = 'rgba(255,255,255,.06)';
    }));
    ['dragleave', 'drop'].forEach((eName) => dropzone.addEventListener(eName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.style.background = 'rgba(255,255,255,.03)';
    }));
    dropzone.addEventListener('drop', (e) => {
      const f = e.dataTransfer?.files?.[0];
      if (f) {
        fileInput.files = e.dataTransfer.files;
        handleFile(f);
      }
    });
    dropzone.addEventListener('click', () => fileInput?.click());
  }

  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      const f = e.target.files?.[0];
      if (f) handleFile(f);
    });
  }

  if (btnExemplo) {
    btnExemplo.addEventListener('click', async () => {
      try {
        const response = await fetch('projetos/xml-para-excel/samples/nfe_exemplo.xml');
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'nfe_exemplo.xml';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (err) {
        console.error(err);
        setStatus('Não consegui baixar o XML de exemplo agora.', 'error');
      }
    });
  }

  if (btnProcessar) {
    btnProcessar.addEventListener('click', () => {
      if (!parsedNota) {
        setStatus('Envie um XML antes de gerar a planilha.', 'error');
        return;
      }
      try {
        const wb = buildWorkbook(parsedNota);
        const sanitizedNumero = (parsedNota.numero || 'nf').toString().replace(/[^\w-]+/g, '_');
        const filename = `nota_${sanitizedNumero || 'xml'}.xlsx`;
        workbookBundle = { wb, filename };
        btnBaixar.disabled = false;
        setStatus('Planilha criada! Clique em "Baixar planilha (Excel)".', 'ok');
      } catch (err) {
        console.error(err);
        setStatus('Não consegui montar a planilha.', 'error');
      }
    });
  }

  if (btnBaixar) {
    btnBaixar.addEventListener('click', () => {
      if (!workbookBundle) {
        setStatus('Gere a planilha antes de baixar.', 'error');
        return;
      }
      XLSX.writeFile(workbookBundle.wb, workbookBundle.filename);
    });
  }
})();
