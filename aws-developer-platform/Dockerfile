FROM python:3.13-slim AS runtime
WORKDIR /app
RUN useradd --create-home --uid 10001 platform
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .
USER platform
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
