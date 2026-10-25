FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py demo.py ./
RUN mkdir /data
ENV DB_PATH=/data/demo.sqlite PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["python", "app.py"]
