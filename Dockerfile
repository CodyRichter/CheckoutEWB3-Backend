
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./src ./src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "4250", "--reload", "--reload-dir", "/app/src", "--log-level", "debug"]