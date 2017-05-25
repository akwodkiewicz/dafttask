FROM python:3
EXPOSE 5000

COPY requirements.txt /requirements.txt

RUN pip install -r /requirements.txt

CMD ["python", "run.py"]
