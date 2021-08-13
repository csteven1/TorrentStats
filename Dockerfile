FROM python:3.7-slim

RUN pip install APScheduler
RUN pip install flask
RUN pip install gunicorn
RUN pip install requests

COPY src src
COPY torrentstats.py ./
COPY gunicorn_config.py ./

EXPOSE 5000
CMD ["gunicorn" , "-b", ":5000", "-c", "gunicorn_config.py", "torrentstats:app"]
