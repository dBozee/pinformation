FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./

ENV PYTHONPATH=${PYTHONPATH}:${PWD} 
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -sSL https://install.python-poetry.org | python3 -

RUN /root/.local/bin/poetry config virtualenvs.create false

RUN /root/.local/bin/poetry install --no-dev

COPY . .

VOLUME ["/app/config"]

ENTRYPOINT ["/root/.local/bin/poetry", "run", "python", "pinformation_bot"]
