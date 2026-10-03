#!/bin/bash

set -e

BITCOIN_DATA="${BITCOIN_DATA:-/data}"

RPC_USER="${BITCOIN_RPC_USER:-deepbsv}"
RPC_PASSWORD="${BITCOIN_RPC_PASSWORD:-deepbsv-internal}"

mkdir -p "${BITCOIN_DATA}"

chown -R bitcoin:bitcoin "${BITCOIN_DATA}"

CONFIG_FILE="${BITCOIN_DATA}/bitcoin.conf"

if [ ! -f "${CONFIG_FILE}" ]; then
    cp /etc/bitcoin/bitcoin.conf "${CONFIG_FILE}"
fi

# ------------------------------------------------------------
# RPC credentials
# ------------------------------------------------------------

if ! grep -q "^rpcuser=" "${CONFIG_FILE}"; then
    echo "rpcuser=${RPC_USER}" >> "${CONFIG_FILE}"
fi

if ! grep -q "^rpcpassword=" "${CONFIG_FILE}"; then
    echo "rpcpassword=${RPC_PASSWORD}" >> "${CONFIG_FILE}"
fi

# ------------------------------------------------------------
# Ensure ownership
# ------------------------------------------------------------

chown bitcoin:bitcoin "${CONFIG_FILE}"

# ------------------------------------------------------------
# Start Bitcoin SV
# ------------------------------------------------------------

if [ "$1" = "bitcoind" ]; then
    shift

    exec gosu bitcoin \
        /usr/local/bin/bitcoind \
        -conf="${CONFIG_FILE}" \
        -datadir="${BITCOIN_DATA}" \
        "$@"
fi

exec "$@"
