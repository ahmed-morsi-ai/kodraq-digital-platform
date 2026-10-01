FROM postgres:16-alpine AS vector_builder
ARG PGVECTOR_VERSION=0.8.6
RUN apk add --no-cache build-base curl \
    && mkdir /tmp/pgvector \
    && curl --fail --location https://github.com/pgvector/pgvector/archive/refs/tags/v${PGVECTOR_VERSION}.tar.gz \
        | tar -xz --strip-components=1 -C /tmp/pgvector \
    && make -C /tmp/pgvector with_llvm=no OPTFLAGS="" \
    && make -C /tmp/pgvector with_llvm=no install \
    && mkdir -p /opt/pgvector/lib /opt/pgvector/extension \
    && cp /usr/local/lib/postgresql/vector.so /opt/pgvector/lib/ \
    && cp /usr/local/share/postgresql/extension/vector* /opt/pgvector/extension/

FROM postgres:16-alpine
COPY --from=vector_builder /opt/pgvector /opt/pgvector
COPY --from=vector_builder /opt/pgvector/lib/ /usr/local/lib/postgresql/
COPY --from=vector_builder /opt/pgvector/extension/ /usr/local/share/postgresql/extension/
