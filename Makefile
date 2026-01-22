.PHONY: docker-run-production docker-run-cron docker-run-dev

docker-run-dev:
	python utils/wait_for_postgres.py || true
	python manage.py migrate --noinput
	python manage.py runserver 0.0.0.0:8000

docker-run-production:
	python utils/wait_for_postgres.py || true
	python manage.py migrate --noinput
	gunicorn vas3k_events.wsgi:application \
		--bind 0.0.0.0:8815 \
		--workers 4 \
		--worker-class sync \
		--worker-connections 1000 \
		--max-requests 1000 \
		--max-requests-jitter 50 \
		--timeout 30 \
		--keep-alive 2 \
		--access-logfile - \
		--error-logfile - \
		--log-level info \
		--capture-output \
		--enable-stdio-inheritance

docker-run-cron:
	crond -f -d 8
