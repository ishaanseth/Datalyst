
FROM python:3.11-slim
WORKDIR /worker
COPY requirements.txt /worker/
RUN pip install --no-cache-dir -r requirements.txt
COPY app /worker/app
ENV PYTHONPATH=/worker
# This worker is an example sandbox runner. In production you'd run a queue consumer here.
CMD ["python", "-c", "print('Worker sandbox ready - implement queue consumer')"]
