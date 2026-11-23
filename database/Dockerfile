# MySQL con los scripts de la base ya incluidos.
# Al crearse el volumen por primera vez, MySQL ejecuta en orden 01 -> 05 (database/init).
FROM mysql:8.0

COPY init/ /docker-entrypoint-initdb.d/

# Los .sql del proyecto se editan en Windows (saltos de línea CRLF). Se pasan a LF para que
# DELIMITER $$ y los triggers se ejecuten bien dentro de Linux.
RUN sed -i 's/\r$//' /docker-entrypoint-initdb.d/*.sql
