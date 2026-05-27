# ← MAL: imagen completa en vez de slim, y corriendo como root
FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# ← MAL: no se define USER, corre como root
# FIX sería agregar:
# RUN addgroup -S appgroup && adduser -S appuser -G appgroup
# USER appuser

EXPOSE 5000

CMD ["python", "app.py"]
