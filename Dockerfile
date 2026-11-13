# API de ABC Software Corp: facturación UBL 2.1, inventario y PLE.
#   docker build -t abc-facturacion .
#   docker run --rm -p 8000:8000 -v abc-datos:/datos abc-facturacion   →  http://localhost:8000/docs
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias primero: la capa se reutiliza mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Código y lo que necesita en ejecución: los XSD oficiales (validación del XML) y los
# ejemplos del contrato (examples del OpenAPI) y la matriz que muestra el formulario /venta.
COPY src ./src
COPY specs/contracts/ubl-2.1/xsd ./specs/contracts/ubl-2.1/xsd
COPY specs/ejemplos ./specs/ejemplos
COPY specs/traceability/matriz.csv ./specs/traceability/matriz.csv

# Nunca como root. Los datos (SQLite) viven en un volumen: sobreviven a reinicios y actualizaciones.
RUN useradd --create-home --uid 10001 abc && mkdir /datos && chown abc /datos
USER abc
ENV ABC_BASE_DATOS=/datos/abc.db
VOLUME ["/datos"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/salud', timeout=2)"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
