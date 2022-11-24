FROM python:3.8

COPY requrements.txt .
COPY .env .
RUN  pip3 install -r requerements.txt


COPY main.py .
CMD ["python3", "main.py"]