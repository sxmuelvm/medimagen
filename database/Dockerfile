# MySQL con los scripts de la base ya incluidos.
# Al crearse el volumen por primera vez, MySQL ejecuta en orden 01 -> 05 (database/init).
FROM mysql:8.0

COPY init/ /docker-entrypoint-initdb.d/

# Los .sql del proyecto se editan en Windows (saltos de línea CRLF). Se pasan a LF para que
# DELIMITER $$ y los triggers se ejecuten bien dentro de Linux.
RUN sed -i 's/\r$//' /docker-entrypoint-initdb.d/*.sql

# Los scripts están en UTF-8 (tildes y ñ). Sin esto, el cliente de MySQL del contenedor los lee
# como latin1 y los datos quedan como "LeÃ³n" en lugar de "León".
RUN printf '[client]\ndefault-character-set=utf8mb4\n\n[mysql]\ndefault-character-set=utf8mb4\n' > /etc/mysql/conf.d/cliente_utf8.cnf
ENV LANG=C.UTF-8
