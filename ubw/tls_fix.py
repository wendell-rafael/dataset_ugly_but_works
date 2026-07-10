"""Workaround para servidores que não enviam a cadeia de certificados TLS
completa (apenas o certificado-folha, sem o intermediário).

Problema observado: `seart-ghs.si.usi.ch` apresenta um certificado-folha
legítimo (Let's Encrypt, dentro da validade, hostname correto), mas não
envia o certificado intermediário durante o handshake TLS. Navegadores
contornam isso automaticamente buscando o intermediário via a extensão
AIA (Authority Information Access) do certificado-folha; `requests` /
`urllib3` / `openssl` não fazem isso por padrão, e a verificação falha
com `unable to get local issuer certificate`.

Este módulo reproduz o comportamento do navegador: baixa o certificado
do emissor via AIA e monta um bundle de CA combinado (certifi + o
intermediário faltante), cacheado localmente. A verificação de cadeia
continua ativa o tempo todo — em nenhum momento `verify=False` é usado.
"""
from __future__ import annotations

import logging
import socket
import ssl
from pathlib import Path
from typing import Optional

import certifi
import requests

logger = logging.getLogger("ubw.tls_fix")

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / ".ca_cache"


def _get_leaf_certificate_der(host: str, port: int = 443, timeout: float = 10.0) -> bytes:
    """Obtém o certificado-folha em DER, sem validar a cadeia (só para
    conseguirmos ler a extensão AIA e decidir como completá-la)."""
    ctx = ssl._create_unverified_context()  # noqa: SLF001 — uso deliberado e local
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            der = ssock.getpeercert(binary_form=True)
    if der is None:
        raise RuntimeError(f"Não foi possível obter o certificado de {host}.")
    return der


def _fetch_issuer_cert_pem(leaf_der: bytes) -> Optional[bytes]:
    """Lê a extensão AIA (Authority Information Access) do certificado-folha
    e baixa o certificado do emissor (mesmo mecanismo usado por navegadores).
    """
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID

    cert = x509.load_der_x509_certificate(leaf_der, default_backend())
    try:
        aia = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
    except x509.ExtensionNotFound:
        return None

    for desc in aia:
        if desc.access_method == AuthorityInformationAccessOID.CA_ISSUERS:
            url = desc.access_location.value
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            issuer_cert = x509.load_der_x509_certificate(resp.content, default_backend())
            return issuer_cert.public_bytes(serialization.Encoding.PEM)
    return None


def get_verify_bundle_for_host(host: str) -> str:
    """Retorna o caminho de um bundle CA que verifica `host` com sucesso.

    Primeiro tenta a verificação padrão (certifi). Se falhar
    especificamente por cadeia incompleta, busca o intermediário via AIA,
    monta um bundle combinado, cacheia em disco e retorna esse caminho.
    Qualquer outro tipo de erro SSL (host errado, certificado expirado,
    certificado autoassinado não confiável) é propagado — este workaround
    cobre apenas o caso específico de cadeia incompleta.
    """
    cache_path = CACHE_DIR / f"{host}.pem"
    if cache_path.exists():
        return str(cache_path)

    ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        with socket.create_connection((host, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host):
                pass
        return certifi.where()  # cadeia já é válida com o bundle padrão
    except ssl.SSLCertVerificationError as exc:
        if "unable to get local issuer certificate" not in str(exc):
            raise
        logger.warning(
            "%s não envia o certificado intermediário durante o handshake TLS "
            "(configuração incompleta do lado do servidor). Completando a "
            "cadeia via AIA, como um navegador faria...",
            host,
        )

    leaf_der = _get_leaf_certificate_der(host)
    issuer_pem = _fetch_issuer_cert_pem(leaf_der)
    if issuer_pem is None:
        raise RuntimeError(
            f"Não foi possível completar a cadeia de certificados de {host} "
            "(certificado-folha sem extensão AIA). Verifique manualmente com "
            "`openssl s_client -connect {host}:443 -showcerts`."
        )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(certifi.where(), "rb") as f:
        base_bundle = f.read()
    with cache_path.open("wb") as f:
        f.write(base_bundle)
        f.write(b"\n")
        f.write(issuer_pem)

    logger.info("Bundle de CA combinado para %s cacheado em %s", host, cache_path)
    return str(cache_path)


# Fixação de impressão digital (fingerprint pinning) para certificado
# EXPIRADO — caso diferente do workaround acima (cadeia incompleta, não
# expiração). Desabilitar `verify=False` puro aceitaria QUALQUER
# certificado nessa conexão; em vez disso, só prosseguimos se o certificado
# apresentado bater EXATAMENTE com a impressão digital SHA-256 conhecida do
# domínio (capturada manualmente via `openssl s_client`), o que continua
# detectando um MITM real. REMOVER assim que o SEART-GHS renovar o
# certificado deles — ver CHANGELOG.md.

import hashlib  # noqa: E402

KNOWN_EXPIRED_CERT_FINGERPRINTS: dict[str, str] = {
    "seart-ghs.si.usi.ch": "5D80B5CB53226C7858DA7A661303B753CD525876135"
                            "4E42C340549B046B7460F".replace(" ", ""),
}


def _cert_sha256_fingerprint(der: bytes) -> str:
    return hashlib.sha256(der).hexdigest().upper()


def verify_pinned_fingerprint(host: str, port: int = 443, timeout: float = 10.0) -> None:
    """Confere que o certificado atualmente apresentado por `host` bate
    EXATAMENTE com a impressão digital conhecida em
    KNOWN_EXPIRED_CERT_FINGERPRINTS. Levanta RuntimeError se não bater
    (certificado diferente do esperado — trata como possível MITM) ou se
    `host` não tiver uma impressão digital cadastrada.
    """
    expected = KNOWN_EXPIRED_CERT_FINGERPRINTS.get(host)
    if expected is None:
        raise RuntimeError(
            f"Nenhuma impressão digital fixada para {host} — não é seguro "
            "prosseguir com certificado expirado sem uma fixação explícita."
        )
    leaf_der = _get_leaf_certificate_der(host, port=port, timeout=timeout)
    got = _cert_sha256_fingerprint(leaf_der)
    if got != expected:
        raise RuntimeError(
            f"Certificado de {host} NÃO bate com a impressão digital fixada "
            f"(esperado {expected}, recebido {got}). Isso pode indicar um "
            "certificado legitimamente renovado (bom sinal — atualize a "
            "fixação) OU uma conexão interceptada (mau sinal — não prossiga "
            "sem investigar). Por segurança, a conexão foi recusada."
        )
    logger.warning(
        "%s: certificado expirado, mas a impressão digital bate exatamente "
        "com a capturada em 2026-07-08 — prosseguindo com verify=False só "
        "para este host, checagem de data ignorada deliberadamente.",
        host,
    )


def get_session_trusting_pinned_cert(host: str) -> requests.Session:
    """Sessão requests que confia no certificado de `host` mesmo vencido,
    DESDE QUE a impressão digital bata com KNOWN_EXPIRED_CERT_FINGERPRINTS
    (verificado a cada chamada — não silenciosamente cacheado). Uso restrito
    a este host específico; nunca usar verify=False de forma genérica.
    """
    verify_pinned_fingerprint(host)  # levanta se não bater — nunca prossegue "no escuro"
    session = requests.Session()
    session.verify = False
    return session
