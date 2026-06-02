FROM python:3.12-slim

WORKDIR /app

# Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# State directory (mount volume for persistence)
RUN mkdir -p /app/state

# Healthcheck — เช็ค heartbeat ทุก 2 นาที
# ถ้า heartbeat เก่า > 5 นาที → unhealthy → Docker restart
HEALTHCHECK --interval=120s --timeout=10s --retries=3 --start-period=180s \
    CMD python3 -c "import sys, json, time; \
    d=json.load(open('state/heartbeat.json')); \
    sys.exit(0 if time.time()-d['unix_ts']<300 and d['status']!='error' else 1)" \
    || exit 1

CMD ["python3", "run.py", "run"]
