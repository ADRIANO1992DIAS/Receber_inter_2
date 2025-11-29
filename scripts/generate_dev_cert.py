"""
Gera certificado e chave autoassinados para desenvolvimento local.

Uso:
    python scripts/generate_dev_cert.py
Gera/atualiza private/devcert.pem (certificado) e private/devkey.pem (chave).
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import ipaddress

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

BASE_DIR = Path(__file__).resolve().parent.parent
PRIVATE_DIR = BASE_DIR / "private"
CERT_PATH = PRIVATE_DIR / "devcert.pem"
KEY_PATH = PRIVATE_DIR / "devkey.pem"


def generate_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def generate_cert(key: rsa.RSAPrivateKey) -> x509.Certificate:
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Receber Inter (dev)"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )

    alt_names = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        x509.IPAddress(ipaddress.ip_address("::1")),
    ]

    now = datetime.now(timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
    )
    return builder.sign(private_key=key, algorithm=hashes.SHA256())


def write_key(key: rsa.RSAPrivateKey, path: Path) -> None:
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.write_bytes(pem)


def write_cert(cert: x509.Certificate, path: Path) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def main():
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)

    key = generate_key()
    cert = generate_cert(key)

    write_key(key, KEY_PATH)
    write_cert(cert, CERT_PATH)

    print(f"Chave escrita em {KEY_PATH}")
    print(f"Certificado escrito em {CERT_PATH}")
    print("Execute: python manage.py runsslserver --certificate private/devcert.pem --key private/devkey.pem")


if __name__ == "__main__":
    main()
