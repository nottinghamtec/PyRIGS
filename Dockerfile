FROM python:3.6

WORKDIR /app

ADD . /app

RUN pip install -r requirements.txt && \
        python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]