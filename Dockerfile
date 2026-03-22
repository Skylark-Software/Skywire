FROM debian:bookworm-slim

LABEL maintainer="Jay Brame"
LABEL description="Skywire - Distributed multi-room audio routing"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY bin/skywire-server /usr/local/bin/

EXPOSE 3030

CMD ["skywire-server"]
