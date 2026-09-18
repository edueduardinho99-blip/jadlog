<?php
// Habilitar CORS para permitir requisições do curso - desbloqueia as magias das cartasend
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Headers: *");
header("Content-Type: application/json");

// Aceitar requisições OPTIONS (preflight CORS)
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Obter o CPF da requisição (suportar JSON e form-data)
$cpf = null;

// Tentar obter do JSON
$json = json_decode(file_get_contents('php://input'), true);
if (isset($json['cpf']) && !empty($json['cpf'])) {
    $cpf = $json['cpf'];
}
// Tentar obter do POST tradicional
elseif (isset($_POST['cpf']) && !empty($_POST['cpf'])) {
    $cpf = $_POST['cpf'];
}

// Verificar se o CPF foi fornecido
if (!$cpf) {
    http_response_code(400);
    echo json_encode(['error' => 'CPF não fornecido']);
    exit;
}

// Limpar o CPF (remover caracteres não numéricos)
$cpf = preg_replace('/[^0-9]/', '', $cpf);

// Verificar se o CPF tem 11 dígitos
if (strlen($cpf) !== 11) {
    http_response_code(400);
    echo json_encode(['error' => 'CPF inválido, deve conter 11 dígitos']);
    exit;
}

// Tokens da API 
$tokens = ["2899"];

$response = null;
$statusCode = null;

foreach ($tokens as $token) {
    $url = "https://searchapi.it.com/consulta?token_api={$token}&cpf={$cpf}";

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Accept: application/json',
        'Content-Type: application/json'
    ]);

    $response = curl_exec($ch);

    if (curl_errno($ch)) {
        curl_close($ch);
        continue;
    }

    $statusCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($statusCode === 200) break;
}

if ($statusCode !== 200) {
    http_response_code($statusCode ?? 500);
    echo json_encode(['error' => 'Erro na API externa', 'status' => $statusCode]);
    exit;
}

// Decodificar a resposta
$data = json_encode(json_decode($response), JSON_PRETTY_PRINT);

// Retornar a resposta
echo $data;
?> 