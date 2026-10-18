FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml /app/
RUN pip install -e .

COPY . /app/
RUN mkdir -p /app/data && mkdir -p /tmp/jarvis_workspace

ENV PYTHONPATH=/app/src
ENV JARVIS_WORKSPACE=/tmp/jarvis_workspace

EXPOSE 8000
CMD ["uvicorn", "jarvis.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
