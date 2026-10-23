#!/bin/sh
# Cria o banco de testes (<POSTGRES_DB>_test), separado do banco de desenvolvimento.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -c "CREATE DATABASE \"${POSTGRES_DB}_test\" OWNER \"${POSTGRES_USER}\";"
