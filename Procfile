release: python manage.py collectstatic --noinput
web: gunicorn distance_erp.wsgi --bind 0.0.0.0:$PORT