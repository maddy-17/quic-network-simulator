FROM martenseemann/quic-network-simulator-endpoint:latest

RUN apt-get update
RUN apt-get install -y libssl-dev python3-dev python3-pip
# Upgrade pip
RUN pip3 install --upgrade pip
RUN pip3 install aiofiles asgiref httpbin starlette wsproto

ARG CONTAINER_PORT
ARG DIR_NAME

COPY . /${DIR_NAME}
WORKDIR /${DIR_NAME}
RUN pip3 install -e .

EXPOSE ${CONTAINER_PORT}/udp

COPY run_endpoint.sh .
RUN chmod +x run_endpoint.sh

ENTRYPOINT [ "./run_endpoint.sh" ]

# CMD ["python", "examples/http3_server.py", "--certificate", "tests/ssl_cert.pem", "--private-key", "tests/ssl_key.pem"]