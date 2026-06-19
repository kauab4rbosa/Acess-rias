<?php
header('Content-Type: text/html; charset=UTF-8');

$result = null;
$error = null;
$cnpj = '';
$token = '';

function formatCNPJ(string $raw): string {
    $digits = preg_replace('/\D/', '', $raw);
    return $digits;
}

function fetchAPI(string $endpoint, string $token): array|false {
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL            => 'https://api.acessorias.com' . $endpoint,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 15,
        CURLOPT_HTTPHEADER     => ['Authorization: Bearer ' . $token],
    ]);
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($response === false || $httpCode === 0) {
        return false;
    }
    return ['code' => $httpCode, 'body' => json_decode($response, true)];
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $cnpj  = trim($_POST['cnpj']  ?? '');
    $token = trim($_POST['token'] ?? '');

    if ($cnpj === '' || $token === '') {
        $error = 'Preencha o CNPJ/CPF e o Token da API.';
    } else {
        $identifier = formatCNPJ($cnpj);
        $res = fetchAPI('/companies/' . urlencode($identifier) . '/?contacts&departments', $token);

        if ($res === false) {
            $error = 'Falha ao conectar com a API. Verifique sua conexão.';
        } elseif ($res['code'] === 401) {
            $error = 'Token inválido ou sem permissão (401).';
        } elseif ($res['code'] === 404) {
            $error = 'Empresa não encontrada para o CNPJ informado (404).';
        } elseif ($res['code'] === 204) {
            $error = 'Nenhum conteúdo retornado pela API (204).';
        } elseif ($res['code'] !== 200) {
            $error = 'Erro inesperado da API (HTTP ' . $res['code'] . ').';
        } else {
            $data = $res['body'];

            // Filter departments: RH - Folha and RH - Impostos
            $rhDepts = [];
            foreach (($data['Departamentos'] ?? []) as $dept) {
                $nome = strtolower($dept['Nome'] ?? '');
                if (str_contains($nome, 'rh') || str_contains($nome, 'folha') || str_contains($nome, 'impost')) {
                    $rhDepts[] = $dept;
                }
            }

            $result = [
                'empresa'    => $data,
                'rh_deptos'  => $rhDepts,
                'contatos'   => $data['ContatosNaEmpresa'] ?? [],
                'todos_deptos' => $data['Departamentos'] ?? [],
            ];
        }
    }
}

function esc(mixed $v): string {
    return htmlspecialchars((string)($v ?? ''), ENT_QUOTES, 'UTF-8');
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contatos RH — Acessórias</title>
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f0f2f5;
            color: #1a1a2e;
            min-height: 100vh;
            padding: 2rem 1rem;
        }

        .container { max-width: 760px; margin: 0 auto; }

        header {
            text-align: center;
            margin-bottom: 2rem;
        }
        header h1 {
            font-size: 1.6rem;
            font-weight: 700;
            color: #b91c1c;
        }
        header p {
            margin-top: .35rem;
            font-size: .9rem;
            color: #555;
        }

        .card {
            background: #fff;
            border-radius: 12px;
            padding: 1.75rem;
            box-shadow: 0 2px 12px rgba(0,0,0,.07);
            margin-bottom: 1.5rem;
        }

        .card h2 {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 1.1rem;
            color: #b91c1c;
            display: flex;
            align-items: center;
            gap: .5rem;
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        @media (max-width: 520px) { .form-row { grid-template-columns: 1fr; } }

        label { display: block; font-size: .82rem; font-weight: 600; margin-bottom: .3rem; color: #444; }

        input[type="text"], input[type="password"] {
            width: 100%;
            padding: .6rem .85rem;
            border: 1.5px solid #ddd;
            border-radius: 7px;
            font-size: .92rem;
            transition: border-color .2s;
        }
        input:focus { outline: none; border-color: #b91c1c; }

        button[type="submit"] {
            background: #b91c1c;
            color: #fff;
            border: none;
            border-radius: 7px;
            padding: .65rem 1.8rem;
            font-size: .95rem;
            font-weight: 600;
            cursor: pointer;
            transition: background .2s;
        }
        button[type="submit"]:hover { background: #991b1b; }

        .alert {
            padding: .85rem 1.1rem;
            border-radius: 8px;
            margin-bottom: 1.2rem;
            font-size: .9rem;
        }
        .alert-error  { background: #fef2f2; border: 1px solid #fca5a5; color: #991b1b; }
        .alert-info   { background: #eff6ff; border: 1px solid #93c5fd; color: #1e40af; }

        .empresa-nome { font-size: 1.15rem; font-weight: 700; color: #111; }
        .empresa-sub  { font-size: .85rem; color: #666; margin-top: .2rem; }
        .badge {
            display: inline-block;
            padding: .15rem .55rem;
            border-radius: 999px;
            font-size: .75rem;
            font-weight: 600;
            margin-left: .4rem;
        }
        .badge-green { background: #dcfce7; color: #166534; }
        .badge-red   { background: #fee2e2; color: #991b1b; }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: .88rem;
        }
        th {
            text-align: left;
            padding: .55rem .75rem;
            background: #fafafa;
            border-bottom: 2px solid #eee;
            font-size: .8rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: .03em;
        }
        td {
            padding: .6rem .75rem;
            border-bottom: 1px solid #f0f0f0;
            color: #222;
        }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: #fafafa; }

        .email-copy {
            font-family: 'Courier New', monospace;
            font-size: .85rem;
            background: #f3f4f6;
            padding: .15rem .4rem;
            border-radius: 4px;
            cursor: pointer;
            user-select: all;
        }
        .empty { text-align: center; padding: 1.5rem; color: #888; font-size: .88rem; }

        .section-title {
            font-size: .78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .07em;
            color: #888;
            margin-bottom: .8rem;
        }

        .highlight-row td { background: #fff7ed; }

        footer {
            text-align: center;
            font-size: .78rem;
            color: #aaa;
            margin-top: 2rem;
        }
    </style>
</head>
<body>
<div class="container">

    <header>
        <h1>Contatos RH por CNPJ</h1>
        <p>Consulte os e-mails dos responsáveis pelos departamentos <strong>RH - Folha</strong> e <strong>RH - Impostos</strong></p>
    </header>

    <div class="card">
        <h2>🔍 Consultar empresa</h2>
        <form method="POST" autocomplete="off">
            <div class="form-row">
                <div>
                    <label for="cnpj">CNPJ / CPF da empresa</label>
                    <input type="text" id="cnpj" name="cnpj"
                           value="<?= esc($cnpj) ?>"
                           placeholder="00.000.000/0000-00"
                           required>
                </div>
                <div>
                    <label for="token">Token da API</label>
                    <input type="password" id="token" name="token"
                           value="<?= esc($token) ?>"
                           placeholder="secret_key"
                           required>
                </div>
            </div>
            <button type="submit">Buscar</button>
        </form>
    </div>

    <?php if ($error): ?>
        <div class="alert alert-error"><?= esc($error) ?></div>
    <?php endif; ?>

    <?php if ($result): ?>
        <?php $emp = $result['empresa']; ?>

        <div class="card">
            <div class="empresa-nome">
                <?= esc($emp['Razao'] ?? '') ?>
                <span class="badge <?= ($emp['Status'] ?? '') === 'Ativa' ? 'badge-green' : 'badge-red' ?>">
                    <?= esc($emp['Status'] ?? '') ?>
                </span>
            </div>
            <div class="empresa-sub">
                <?= esc($emp['Fantasia'] ?? '') ?>
                &nbsp;·&nbsp;
                <?= esc($emp['Identificador'] ?? '') ?>
                <?php if (!empty($emp['Regime'])): ?>
                    &nbsp;·&nbsp; <?= esc($emp['Regime']) ?>
                <?php endif; ?>
            </div>
        </div>

        <!-- RH Departments -->
        <div class="card">
            <h2>👥 Responsáveis — RH Folha & RH Impostos</h2>
            <?php if (empty($result['rh_deptos'])): ?>
                <div class="alert alert-info">Nenhum departamento com "RH", "Folha" ou "Imposto" encontrado nesta empresa.</div>
            <?php else: ?>
                <table>
                    <thead>
                        <tr>
                            <th>Departamento</th>
                            <th>Responsável</th>
                            <th>E-mail</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($result['rh_deptos'] as $dept): ?>
                        <tr class="highlight-row">
                            <td><?= esc($dept['Nome']) ?></td>
                            <td><?= esc($dept['RespNome'] ?? '—') ?></td>
                            <td>
                                <?php if (!empty($dept['RespEmail'])): ?>
                                    <span class="email-copy" title="Clique para selecionar"><?= esc($dept['RespEmail']) ?></span>
                                <?php else: ?>
                                    <span style="color:#aaa">—</span>
                                <?php endif; ?>
                            </td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php endif; ?>
        </div>

        <!-- All contacts -->
        <?php if (!empty($result['contatos'])): ?>
        <div class="card">
            <h2>📋 Contatos cadastrados na empresa</h2>
            <p style="font-size:.82rem;color:#888;margin-bottom:1rem;">
                A API retorna todos os contatos da empresa. Para filtragem por departamento individual (como RH - Folha ou RH - Impostos por contato), utilize o painel do Acessórias.
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Nome</th>
                        <th>E-mail</th>
                        <th>Celular</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($result['contatos'] as $c): ?>
                    <tr>
                        <td><?= esc($c['Nome'] ?? '') ?></td>
                        <td>
                            <?php if (!empty($c['E-mail'])): ?>
                                <span class="email-copy"><?= esc($c['E-mail']) ?></span>
                            <?php else: ?>
                                <span style="color:#aaa">—</span>
                            <?php endif; ?>
                        </td>
                        <td><?= esc($c['Celular'] ?? '—') ?></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
        <?php endif; ?>

        <!-- All departments (collapsed) -->
        <?php if (!empty($result['todos_deptos'])): ?>
        <div class="card">
            <details>
                <summary style="cursor:pointer;font-size:.9rem;font-weight:600;color:#555;">
                    Todos os departamentos (<?= count($result['todos_deptos']) ?>)
                </summary>
                <table style="margin-top:1rem;">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Departamento</th>
                            <th>Responsável</th>
                            <th>E-mail</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($result['todos_deptos'] as $dept): ?>
                        <tr>
                            <td style="color:#aaa"><?= esc($dept['ID']) ?></td>
                            <td><?= esc($dept['Nome']) ?></td>
                            <td><?= esc($dept['RespNome'] ?? '—') ?></td>
                            <td>
                                <?php if (!empty($dept['RespEmail'])): ?>
                                    <span class="email-copy"><?= esc($dept['RespEmail']) ?></span>
                                <?php else: ?>
                                    <span style="color:#aaa">—</span>
                                <?php endif; ?>
                            </td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </details>
        </div>
        <?php endif; ?>

    <?php endif; ?>

    <footer>Integração com api.acessorias.com — limite de 100 req/min</footer>
</div>
</body>
</html>
