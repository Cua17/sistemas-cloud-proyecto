# Imagen del simulador de dispositivos IoT (ARM64).
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY patterns.py simulator.py ./

# Corre como usuario sin privilegios
RUN useradd -m app && chown -R app /app
USER app

CMD ["python", "-u", "simulator.py"]
