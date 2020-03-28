# this is an official Python runtime, used as the parent image
FROM python:3.6.5-slim

ADD . /app
WORKDIR /app
RUN apt-get update && apt-get install netcat -y
RUN pip install -r requirements.txt
# unblock port 80 for the Flask app to run on
WORKDIR /app
ADD . /app/datajoint-python
RUN pip install -e datajoint-python
EXPOSE 1234
EXPOSE 3306
COPY ./docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
