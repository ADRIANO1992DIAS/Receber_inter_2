"""
Sobe o servidor de desenvolvimento em HTTPS.
- Gera certificado/chave autoassinados em private/ se nao existirem.
- Usa django-sslserver com a porta 8000.

Uso:
    python scripts/run_https_dev.py
"""

from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
CERT_PATH = BASE_DIR / "private" / "devcert.pem"
KEY_PATH = BASE_DIR / "private" / "devkey.pem"


def ensure_certificates() -> None:
    if CERT_PATH.exists() and KEY_PATH.exists():
        return
    print("Gerando certificado autoassinado (faltava devcert/devkey)...")
    subprocess.run([sys.executable, "scripts/generate_dev_cert.py"], check=True)


def run_sslserver() -> None:
    cmd = [
        sys.executable,
        "manage.py",
        "runsslserver",
        "0.0.0.0:8000",
        "--certificate",
        str(CERT_PATH),
        "--key",
        str(KEY_PATH),
    ]
    print("Iniciando django-sslserver em https://0.0.0.0:8000 ...")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    ensure_certificates()
    run_sslserver()
