# YottaDB infrastructure (U01 + U02)

Live config for YottaDB r2.06, the YDB Web Server plugin, and Caddy TLS on:

| Host | Name | LAN | Tailscale |
|------|------|-----|-----------|
| U01 | utility-01 / `home.flamingyak.com` | 192.168.0.16 | 100.72.84.8 |
| U02 | utility-02 / `utility-02.taild03114.ts.net` | 192.168.0.24 | 100.89.100.53 |

## Layout

```
common/ydb-web-server           # start/stop wrapper (sources ydb_env_set)
common/ydb-web-server.service   # systemd unit (User=mark, :9080)
common/caddy-auth.conf          # fail2ban filter for Caddy 4xx scanners
u01/Caddyfile                   # Let's Encrypt for home.flamingyak.com
u01/jail.local                  # fail2ban: sshd + caddy-scanners
u02/Caddyfile                   # tls internal (no public DNS on U02)
u02/jail.local
```

## Services

| Service | Port | Notes |
|---------|------|-------|
| YottaDB Web Server | 9080 (LAN/Tailscale) | `ydb-web-server.service` |
| Caddy | 80/443 | TLS terminator; proxy → :9080 |

- **U01 public URL:** `https://home.flamingyak.com/ydb/*` (prefix stripped) and default `/` → YottaDB. `/health` is a local JSON check. Let's Encrypt for `home.flamingyak.com`.
- **U02 public URL:** `https://utility-02/` (also `https://192.168.0.24/`, `https://100.89.100.53/`, `https://utility-02.taild03114.ts.net/`). Caddy **local CA** (`tls internal`) because U02 has no public A record. Client CA: `/var/ydb/caddy-root.crt` (also `/var/ydb/caddy-chain.pem`). `caddy trust` installs it into the system store.

## Install (reference)

```bash
# YottaDB + web server plugin
curl -sL -o ydbinstall.sh https://gitlab.com/YottaDB/DB/YDB/raw/master/sr_unix/ydbinstall.sh
chmod +x ydbinstall.sh
sudo ./ydbinstall.sh --utf8 --webserver --force-install
```

Install path: `/usr/local/lib/yottadb/r206`. Env: `source /usr/local/etc/ydb_env_set`.

## Firewall / fail2ban

**UFW (both):** `22/tcp`, `80/tcp`, `443/tcp`, `41641/udp` open to anywhere. `9080/tcp` **LAN/Tailscale only** (`192.168.0.0/16`, `100.64.0.0/10`, `10.0.0.0/8`, `172.16.0.0/12`). U01 also has scanner /24 DENY rules.

**fail2ban (both):** `sshd` + `caddy-scanners` (`caddy-auth.conf` on `/var/log/caddy/access.log`).

## Smoke

```bash
# U01
curl --resolve home.flamingyak.com:443:127.0.0.1 https://home.flamingyak.com/ydb/api/ping
curl --resolve home.flamingyak.com:443:127.0.0.1 https://home.flamingyak.com/ydb/api/version

# U02 (system trust after `caddy trust`, or --cacert)
curl --cacert /var/ydb/caddy-root.crt --resolve utility-02:443:127.0.0.1 https://utility-02/api/ping
curl --cacert /var/ydb/caddy-root.crt https://192.168.0.24/api/version
```

## Notes

- `ydb_env_set` is **not** `set -u` safe — wrappers use `set -eo pipefail` only.
- U02 sudo needs the account password (`echo "<pw>" | sudo -S -p '' cmd`). Do not pair `sudo -S` with a heredoc (steals password stdin). U01 has NOPASSWD sudo.
- U02 local-CA leaf certs are 12h and auto-renew (Caddy 2.11 default).
- `ydbinstall` sets `RemoveIPC=no` in `logind.conf`; logind was restarted on both hosts.
