FROM python:3.12-slim

WORKDIR /app

COPY src /app/src
COPY data /app/data-seed
COPY README.md requirements.txt /app/
COPY entrypoint.sh /usr/local/bin/zupoo-entrypoint.sh

RUN sed -i 's/\r$//' /usr/local/bin/zupoo-entrypoint.sh \
    && chmod +x /usr/local/bin/zupoo-entrypoint.sh

EXPOSE 8081

ENTRYPOINT ["/usr/local/bin/zupoo-entrypoint.sh"]
