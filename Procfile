release: python manage.py migrate --noinput --fake-initial
web: gunicorn config.wsgi --log-file -
