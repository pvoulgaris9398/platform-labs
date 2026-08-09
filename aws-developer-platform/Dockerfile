# ---- Stage 1: build ----
# Installs the package into an isolated venv. This stage is discarded
# after the build, so pip's cache, wheel files, and build metadata
# never end up in the final image.
FROM python:3.13-slim AS builder

WORKDIR /app

# Create the venv we'll copy into the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --no-cache-dir .

# ---- Stage 2: runtime ----
# Fresh slim base with no build tooling, no pyproject.toml/README.md,
# no pip cache -- just the venv and the app source.
FROM python:3.13-slim AS runtime

WORKDIR /app

RUN useradd --create-home --uid 10001 platform

# Bring in only the installed packages from the builder stage.
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# App source needs to be present at runtime too (uvicorn imports app.main).
COPY app ./app

USER platform
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
