FROM alpine:latest

ARG VERSION
LABEL "org.opencontainers.image.vendor"="anthonyuk.dev"
LABEL "org.opencontainers.image.version"="${VERSION}"

COPY ./cert-sync.py /usr/local/bin/

RUN \
	apk add --no-cache python3 py3-pip git \
	&& python -m venv /usr/local/share/truenas-cert-sync \
	&& /usr/local/share/truenas-cert-sync/bin/pip install git+https://github.com/truenas/api_client.git \
	&& apk del --no-cache git py3-pip \
	&& sed -i "s/__version__ = .*/__version__ = '${VERSION}'/" /usr/local/bin/cert-sync.py

WORKDIR /usr/local/bin
VOLUME /certs

ENV TRUENAS_SYNC_CA=/certs/ca.crt
ENV TRUENAS_SYNC_CERT=/certs/tls.crt
ENV TRUENAS_SYNC_KEY=/certs/tls.key

ENTRYPOINT ["/usr/local/bin/cert-sync.py"]
