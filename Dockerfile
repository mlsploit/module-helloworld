FROM python:3.6-alpine

VOLUME /mnt/input
VOLUME /mnt/output

COPY . /app
WORKDIR /app

CMD ["sh", "run.sh"]
