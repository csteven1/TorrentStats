FROM python:3.8-slim

RUN pip install APScheduler
RUN pip install flask
RUN pip install requests
RUN pip install waitress

COPY src src
COPY torrentstats.py ./

EXPOSE 5656
CMD ["waitress-serve", "--port=5656", "--threads=6", "torrentstats:app"]