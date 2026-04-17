"""
ETL: Oracle (BO/GDF) → JSON.GZ → GitHub Releases
Extrai dados via oracledb, comprime com gzip e salva em data/gz/
para upload no Release 'dados-latest' do GitHub.
Os dashboards consomem os arquivos diretamente do Release.
"""

import os
import json
import gzip
import logging
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

# ── Variáveis de ambiente ──────────────────────────────────────────────────
load_dotenv()

DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN      = os.getenv("DB_DSN", "10.69.1.118:1521/oraprd06")
CLIENT_PATH = os.getenv("ORACLE_CLIENT_PATH", "").strip()
DB_MIN  = int(os.getenv("DB_MIN_CONNECTIONS", 1))
DB_MAX  = int(os.getenv("DB_MAX_CONNECTIONS", 5))
DB_INC  = int(os.getenv("DB_INCREMENT_CONNECTIONS", 1))

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Caminhos ───────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
OUTPUT_DIR  = BASE_DIR / "data"
GZ_DIR      = BASE_DIR / "data" / "gz"
QUERIES_DIR = BASE_DIR / "data" / "queries"
OUTPUT_DIR.mkdir(exist_ok=True)
GZ_DIR.mkdir(exist_ok=True)

# Schema Oracle dinâmico: mil2026, mil2027, ...
SCHEMA_ANO = f"mil{datetime.now().year}"


# ──────────────────────────────────────────────────────────────────────────
#  QUERIES
#
#  Cada item aceita:
#    "file"     → nome do arquivo JSON gerado em data/
#    "sql_file" → nome do arquivo .sql dentro de data/queries/
#                 (suporte ao placeholder {SCHEMA_ANO})
# ──────────────────────────────────────────────────────────────────────────
QUERIES = [
    {
        # Saldo contábil por função e subfunção (dashboard funcao-subfuncao)
        "file": "saldo_funcao_subfuncao.json",
        "sql_file": "saldocontabil_funcao_subfuncao.sql",
    },
    {
        # Receita Orçamentária (Balanço Orçamentário)
        "file": "receita.json",
        "sql_file": "RECEITA.sql",
    },
    {
        # Despesa Orçamentária — arquivo grande (>100 MB), hospedado no GitHub Releases
        "file": "despesa.json",
        "sql_file": "DESPESA.sql",
    },
    {
        # Créditos Adicionais — hospedado no GitHub Releases
        "file": "creditos_adicionais.json",
        "sql_file": "CREDITOS_ADICIONAIS.sql",
    },
    # Adicione mais queries aqui seguindo o mesmo padrão.
]


# ── Helpers ────────────────────────────────────────────────────────────────

def serialize(value):
    """Converte tipos Oracle não serializáveis em JSON."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def fetch(cursor, query: str) -> list[dict]:
    """Executa query e retorna lista de dicionários."""
    cursor.execute(query)
    columns = [col[0].lower() for col in cursor.description]
    return [
        {col: serialize(val) for col, val in zip(columns, row)}
        for row in cursor.fetchall()
    ]


def save_json(filename: str, data: list[dict]):
    """Salva dados como JSON com metadados de atualização."""
    payload = {
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "total": len(data),
        "dados": data,
    }
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"  ✓ {filename} — {len(data)} registros salvos")


def save_json_gz(filename: str, data: list[dict]):
    """
    Salva dados como JSON comprimido com gzip (compresslevel=9).
    Gera <filename>.gz em data/gz/ para upload no GitHub Releases.
    Redução típica: 70-85% do tamanho original.
    """
    payload = {
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "total": len(data),
        "dados": data,
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    gz_filename = filename + ".gz"
    path = GZ_DIR / gz_filename
    with gzip.open(path, "wb", compresslevel=9) as f:
        f.write(content)
    size_kb = path.stat().st_size / 1024
    log.info(f"  ✓ {gz_filename} — {len(data)} registros, {size_kb:.1f} KB comprimido")


def read_sql(filename: str) -> str:
    """
    Lê arquivo .sql de data/queries/,
    remove comentários de linha (--) e substitui {SCHEMA_ANO}.
    """
    path = QUERIES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Arquivo SQL não encontrado: {path}")
    sql = path.read_text(encoding="utf-8")
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    return "\n".join(lines).replace("{SCHEMA_ANO}", SCHEMA_ANO).strip()


def resolve_query(item: dict) -> str:
    """Retorna o SQL lido do arquivo em data/queries/."""
    return read_sql(item["sql_file"])


# ── Oracle ─────────────────────────────────────────────────────────────────

def init_oracle():
    """
    Inicializa oracledb.
    - Thick mode se ORACLE_CLIENT_PATH estiver definido no .env
    - Thin mode caso contrário (Oracle 12.1+, sem client instalado)
    """
    import oracledb

    if CLIENT_PATH:
        log.info(f"Inicializando thick mode → {CLIENT_PATH}")
        oracledb.init_oracle_client(lib_dir=CLIENT_PATH)
    else:
        log.info("Usando thin mode (sem Oracle Client local)")

    return oracledb


# ── Pipeline principal ─────────────────────────────────────────────────────

def run():
    try:
        oracledb = init_oracle()
    except ImportError:
        raise ImportError("Execute: pip install oracledb")

    if not DB_USER or not DB_PASSWORD:
        raise ValueError("DB_USER e DB_PASSWORD precisam estar definidos no .env")

    log.info(f"Conectando ao Oracle → {DB_DSN}  [schema: {SCHEMA_ANO}]")

    pool = oracledb.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        min=DB_MIN,
        max=DB_MAX,
        increment=DB_INC,
    )

    with pool.acquire() as conn:
        log.info("Conexão estabelecida. Iniciando extração...")
        with conn.cursor() as cur:
            for item in QUERIES:
                log.info(f"Extraindo → {item['file']}")
                try:
                    data = fetch(cur, resolve_query(item))
                    save_json(item["file"], data)
                    save_json_gz(item["file"], data)
                except Exception as e:
                    log.error(f"  ✗ Erro em {item['file']}: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()

    pool.close()
    log.info("ETL concluído com sucesso.")


if __name__ == "__main__":
    run()
