FROM python:3.6-slim

LABEL maintainer "magnus@thinkware.se, phoenix@pagero.com"

RUN apt-get -y update && apt-get -y install build-essential
WORKDIR /usr/src/mail2alert
COPY . /usr/src/mail2alert
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONPATH /usr/src/mail2alert/src

CMD [ "python", "./mail2alert" ]
