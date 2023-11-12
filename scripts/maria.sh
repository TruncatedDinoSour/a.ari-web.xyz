#!/usr/bin/env sh

set -e

gen_pw() {
    head -c 128 /dev/urandom | base64 -w 0 | sed 's/[^A-Za-z0-9]//g' | head -c 79
}

main() {
    if [ "$(id -u)" -ne 0 ]; then
        echo 'run me as root' >&2
        exit 1
    fi

    if [ ! "$1" ]; then
        echo 'supply maria config in the first arg, usually /etc/my.cnf or /etc/mysql/my.cnf' >&2
        exit 1
    fi

    stty -echo
    printf 'system root password : ' >&2
    read -r root_pw
    stty echo

    echo >&2
    echo 'generating main db ...' >&2

    user="$(gen_pw)"
    user_pw="$(gen_pw)"
    gen_root_pw="$(gen_pw)"

    systemctl stop mariadb >/dev/null

    cat >"$1" <<EOF
[client-server]
!includedir /etc/my.cnf.d

[mysqld]
bind-address = 127.0.0.1
EOF

    rm -rf /var/lib/mysql/
    mkdir -p /var/lib/mysql/

    mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql >/dev/null
    systemctl enable --now mariadb >/dev/null

    mariadb --user=root --password="$root_pw" --host=localhost >/dev/null <<EOF
START TRANSACTION;

UPDATE mysql.global_priv SET priv=json_set(priv, '\$.plugin', 'mysql_native_password', '\$.authentication_string', PASSWORD('$gen_root_pw')) WHERE User='root';
FLUSH PRIVILEGES;
DELETE FROM mysql.global_priv WHERE User='' OR Host NOT IN ('127.0.0.1', 'localhost', '::1');
FLUSH PRIVILEGES;

DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';

CREATE DATABASE main;
CREATE USER '$user'@'127.0.0.1' IDENTIFIED BY '$user_pw';
GRANT ALL PRIVILEGES ON main.* TO '$user'@'127.0.0.1';

FLUSH PRIVILEGES;

COMMIT;
EOF

    cat <<EOF
#!/bin/sh
# auto-generated by $0 at $(date)
export MARIA_USER="$user"
export MARIA_PASS="$user_pw"
EOF

    echo "root pw : $gen_root_pw" >&2
}

main "$@"
