FROM python:3.11.13-slim-bookworm@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1 AS builder

WORKDIR /build

COPY pyproject.toml .
COPY app ./app

# Install only production dependencies into a clean prefix. Build tooling and
# test dependencies remain in this discarded stage.
RUN python -m pip install --no-cache-dir --prefix=/install .


FROM python:3.11.13-slim-bookworm@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y \
    && python -m pip uninstall -y pip setuptools wheel \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && rm -rf /var/lib/apt/lists/* /root/.cache

COPY --from=builder /install /usr/local
COPY alembic.ini .
COPY alembic ./alembic

USER 10001:10001

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
