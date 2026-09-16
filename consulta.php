<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}
header('Content-Type: application/json; charset=utf-8');

function send_json_response($nome, $error = null) {
    $response = ['nome' => $nome];
    if ($error !== null) {
        $response['error'] = $error;
    }
    echo json_encode($response, JSON_UNESCAPED_UNICODE);
    exit;
}

function handle($cpf) {
    return preg_replace('/\D/', '', $cpf ?? '');
}

$cpf = isset($_GET['cpf']) ? handle($_GET['cpf']) : '';

if (empty($cpf)) {
    send_json_response('', 'CPF não informado');
}

if (strlen($cpf) !== 11) {
    send_json_response('', 'CPF inválido');
}

$url = 'https://api.doctorclin.com.br/v2/datasus/cpf/' . $cpf;
$apiKey = '5406b859a736396b3d512a84e3a2fecf';

$ch = curl_init($url);
$headers = [
    "Authorization: Api-Key $apiKey",
    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Content-Type: application/json",
    "Origin: https://empresa.doctorclin.com.br"
];

curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => $headers,
    CURLOPT_ENCODING => '',
    CURLOPT_TIMEOUT => 30
]);

$response = curl_exec($ch);
if ($response === false) {
    send_json_response('', "Erro cURL: " . curl_error($ch));
}
curl_close($ch);

$data = json_decode($response, true);

if (!isset($data['stauts']) || !$data['stauts']) {
    $erroMsg = isset($data['mensagem']) ? $data['mensagem'] : 'API retornou status falso';
    send_json_response('', $erroMsg);
}

$nomeCompleto = '';
if (isset($data['data']['cadsus']['nomeCompleto'])) {
    $nomeCompleto = mb_strtoupper(trim($data['data']['cadsus']['nomeCompleto']), 'UTF-8');
}

send_json_response($nomeCompleto);