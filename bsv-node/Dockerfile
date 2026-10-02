FROM debian:bookworm AS builder

ARG BSV_VERSION=v1.2.2

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    autoconf \
    automake \
    build-essential \
    ca-certificates \
    curl \
    git \
    libboost-all-dev \
    libdb-dev \
    libdb++-dev \
    libevent-dev \
    libminiupnpc-dev \
    libssl-dev \
    libtool \
    pkg-config \
    python3 \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

RUN git clone --branch ${BSV_VERSION} --depth 1 \
    https://github.com/bitcoin-sv/bitcoin-sv.git bitcoin-sv

WORKDIR /opt/bitcoin-sv

RUN ./autogen.sh && \
    ./configure \
        --disable-tests \
        --disable-bench \
        --without-gui \
        --disable-wallet && \
    make -j"$(nproc)"

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libboost-system1.81.0 \
    libboost-filesystem1.81.0 \
    libboost-thread1.81.0 \
    libboost-program-options1.81.0 \
    libboost-chrono1.81.0 \
    libevent-2.1-7 \
    libminiupnpc17 \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/bitcoin-sv/src/bitcoind /usr/local/bin/bitcoind
COPY --from=builder /opt/bitcoin-sv/src/bitcoin-cli /usr/local/bin/bitcoin-cli

RUN mkdir -p /data

WORKDIR /data

EXPOSE 8332 8333

VOLUME ["/data"]

ENTRYPOINT ["bitcoind"]
