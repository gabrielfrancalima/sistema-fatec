.PHONY: up down logs test rebuild clean

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	docker compose exec -e REACT_APP_BACKEND_URL=http://127.0.0.1:8000 backend pytest -v

rebuild:
	docker compose build --no-cache && docker compose up -d

clean:
	docker compose down -v
