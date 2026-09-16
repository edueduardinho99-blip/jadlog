const inputFormatado = document.getElementById('cpf');
  const inputReal = document.getElementById('cpf_real');

  inputFormatado.addEventListener('input', function () {
    let valor = inputFormatado.value.replace(/\D/g, ''); // remove tudo que não for número

    // aplica a formatação: 000.000.000-00
    if (valor.length > 3) {
      valor = valor.replace(/^(\d{3})(\d)/, '$1.$2');
    }
    if (valor.length > 6) {
      valor = valor.replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3');
    }
    if (valor.length > 9) {
      valor = valor.replace(/^(\d{3})\.(\d{3})\.(\d{3})(\d)/, '$1.$2.$3-$4');
    }

    inputFormatado.value = valor;
  });

  document.getElementById('meuFormulario').addEventListener('submit', function () {
    // remove a formatação antes de enviar
    inputReal.value = inputFormatado.value.replace(/\D/g, '');
  });