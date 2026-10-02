FROM debian:bookworm AS builder

ARG BSV_VERSION=v1.2.2

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ca-certificates \
    git \
    autoconf \
    automake \
    build-essential \
    libtool \
    pkg-config \
    bsdmainutils \
    python3 \
    g++ \
    libssl-dev \
    libevent-dev \
    libdb-dev \
    libdb++-dev \
    libminiupnpc-dev \
    libzmq3-dev \
    libgoogle-perftools-dev \
    libboost-system-dev \
    libboost-filesystem-dev \
    libboost-chrono-dev \
    libboost-program-options-dev \
    libboost-test-dev \
    libboost-thread-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

RUN git clone \
    --branch ${BSV_VERSION} \
    --depth 1 \
    https://github.com/bitcoin-sv/bitcoin-sv.git \
    bitcoin-sv

WORKDIR /opt/bitcoin-sv

RUN ./autogen.sh && \
    ./configure \
        --disable-tests \
        --disable-bench \
        --without-gui \
        --disable-wallet && \
    make -j"$(nproc)"

# ------------------------------------------------------------
# Runtime image
# ------------------------------------------------------------

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ca-certificates \
    gosu \
    libatomic1 \
    libssl3 \
    libevent-2.1-7 \
    libminiupnpc17 \
    libzmq5 \
    libgoogle-perftools4 \
    libboost-system1.74.0 \
    libboost-filesystem1.74.0 \
    libboost-chrono1.74.0 \
    libboost-program-options1.74.0 \
    libboost-thread1.74.0 \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Bitcoin SV user
# ------------------------------------------------------------

RUN groupadd --gid 1000 bitcoin && \
    useradd \
        --uid 1000 \
        --gid 1000 \
        --create-home \
        --home-dir /home/bitcoin \
        --shell /usr/sbin/nologin \
        bitcoin

# ------------------------------------------------------------
# BSV binaries
# ------------------------------------------------------------

COPY --from=builder /opt/bitcoin-sv/src/bitcoind \
    /usr/local/bin/bitcoind

COPY --from=builder /opt/bitcoin-sv/src/bitcoin-cli \
    /usr/local/bin/bitcoin-cli

COPY --from=builder /opt/bitcoin-sv/src/bitcoin-tx \
    /usr/local/bin/bitcoin-tx

# ------------------------------------------------------------
# Configuration + entrypoint
# ------------------------------------------------------------

COPY bitcoin.conf /etc/bitcoin/bitcoin.conf
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod +x /usr/local/bin/docker-entrypoint.sh && \
    mkdir -p /data && \
    chown -R bitcoin:bitcoin /data

WORKDIR /data

VOLUME ["/data"]

EXPOSE 8332 8333

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

CMD ["bitcoind"]
