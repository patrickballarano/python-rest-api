build:
    docker compose up --build -d --remove-orphans
up:
    docker compose up -d
down:
    docker compose down -v
show_logs:
    docker compose logs