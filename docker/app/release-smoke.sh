#!/usr/bin/env bash
set -euo pipefail

image="${1:-djaapp:local}"
network="djaapp-release-smoke-network-$$"
database="djaapp-release-smoke-db-$$"
container="djaapp-release-smoke-web-$$"
port=""

cleanup() {
    docker rm -f "$container" >/dev/null 2>&1 || true
    docker rm -f "$database" >/dev/null 2>&1 || true
    docker network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT

web_diagnostics() {
    docker inspect "$container" >&2 || true
    docker logs --tail 100 "$container" >&2 || true
}

database_diagnostics() {
    docker logs --tail 100 "$database" >&2 || true
}

docker image inspect "$image" >/dev/null
docker network create "$network" >/dev/null
docker run -d --rm --name "$database" --network "$network" --network-alias database \
    -e POSTGRES_DB=release_verification \
    -e POSTGRES_USER=release_verification \
    -e POSTGRES_PASSWORD=release_verification \
    postgres:16-alpine >/dev/null

database_ready=0
for _ in $(seq 1 30); do
    if docker exec "$database" pg_isready -U release_verification -d release_verification >/dev/null 2>&1; then
        database_ready=1
        break
    fi
    sleep 1
done

if [ "$database_ready" -ne 1 ]; then
    echo "release smoke failed: disposable PostgreSQL did not become ready" >&2
    database_diagnostics
    exit 1
fi

docker run --rm --network "$network" \
    -e DEBUG=False \
    -e DJANGO_ENV=verification \
    -e SECRET_KEY=release-verification-synthetic-secret \
    -e ALLOWED_HOSTS=localhost,127.0.0.1 \
    -e DATABASE_URL=postgres://release_verification:release_verification@database:5432/release_verification \
    -e DATABASE_SSL_REQUIRE=False \
    -e SECURE_SSL_REDIRECT=False \
    -e TASKS_BACKEND=django.tasks.backends.dummy.DummyBackend \
    "$image" python backend/manage.py migrate --noinput >/dev/null

docker run -d --rm --name "$container" --network "$network" -p 127.0.0.1::8000 \
    -e DEBUG=False \
    -e DJANGO_ENV=verification \
    -e SECRET_KEY=release-verification-synthetic-secret \
    -e ALLOWED_HOSTS=localhost,127.0.0.1 \
    -e DATABASE_URL=postgres://release_verification:release_verification@database:5432/release_verification \
    -e DATABASE_SSL_REQUIRE=False \
    -e SECURE_SSL_REDIRECT=False \
    -e TASKS_BACKEND=django.tasks.backends.dummy.DummyBackend \
    "$image" >/dev/null

port="$(docker port "$container" 8000/tcp | sed -n 's/.*:\([0-9][0-9]*\)$/\1/p')"
if [ -z "$port" ]; then
    echo "release smoke failed: container port was not published" >&2
    web_diagnostics
    exit 1
fi

runtime_uid="$(docker exec "$container" id -u)"
if [ "$runtime_uid" = "0" ]; then
    echo "release smoke failed: runtime container is running as root" >&2
    web_diagnostics
    exit 1
fi

for _ in $(seq 1 30); do
    status="$(curl --connect-timeout 1 --max-time 2 --silent --output /dev/null --write-out '%{http_code}' "http://127.0.0.1:${port}/dashboard/login/" || true)"
    if [ "$status" = "200" ]; then
        health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container")"
        case "$health" in
            healthy)
                echo "release smoke passed: image=$image uid=$runtime_uid liveness=/dashboard/login/"
                exit 0
                ;;
        esac
    fi
    sleep 1
done

echo "release smoke failed: liveness or Docker healthcheck did not pass" >&2
web_diagnostics
exit 1
