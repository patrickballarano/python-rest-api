FROM python:3.10-slim-bullseye

#set workdir
WORKDIR /var/server

# set env
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update && apt-get install -y netcat

ADD requirements.txt /tmp/requirements.txt

# if issues with pip add: pip debug -v
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . /var/server

CMD python /var/server/rest-api/app/app.py

