import re
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

API_BASE = "https://api.acessorias.com"
RH_KEYWORDS = ("rh", "folha", "imposto")


def clean_identifier(value: str) -> str:
    return re.sub(r"\D", "", value)


def is_rh_dept(name: str) -> bool:
    return any(kw in name.lower() for kw in RH_KEYWORDS)


def fetch_company(identifier: str, token: str) -> tuple[dict | None, str | None]:
    url = f"{API_BASE}/companies/{identifier}/?contacts&departments"
    try:
        res = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    except requests.exceptions.ConnectionError:
        return None, "Falha ao conectar com a API. Verifique sua conexão."
    except requests.exceptions.Timeout:
        return None, "A API demorou demais para responder (timeout)."

    if res.status_code == 401:
        return None, "Token inválido ou sem permissão (401)."
    if res.status_code == 404:
        return None, "Empresa não encontrada para o CNPJ informado (404)."
    if res.status_code == 204:
        return None, "Nenhum dado retornado pela API (204)."
    if res.status_code == 429:
        return None, "Limite de requisições atingido. Aguarde um momento (429)."
    if res.status_code != 200:
        return None, f"Erro inesperado da API (HTTP {res.status_code})."

    return res.json(), None


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    cnpj = ""
    token = ""

    if request.method == "POST":
        cnpj = request.form.get("cnpj", "").strip()
        token = request.form.get("token", "").strip()

        if not cnpj or not token:
            error = "Preencha o CNPJ/CPF e o Token da API."
        else:
            identifier = clean_identifier(cnpj)
            data, error = fetch_company(identifier, token)

            if data:
                deptos = data.get("Departamentos") or []
                result = {
                    "empresa": data,
                    "rh_deptos": [d for d in deptos if is_rh_dept(d.get("Nome", ""))],
                    "contatos": data.get("ContatosNaEmpresa") or [],
                    "todos_deptos": deptos,
                }

    return render_template("index.html", result=result, error=error, cnpj=cnpj, token=token)


if __name__ == "__main__":
    app.run(debug=True, port=8080)
