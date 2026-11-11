# Homelab password manager

URL: https://passwords.yashbhangale.site

Vaultwarden 1.37.5 with bundled web vault 2026.10.1. Use the Bitwarden web,
browser, mobile, or desktop client with this self-hosted server URL.

## Owner account and imported credentials

The owner account and generated master password are recorded **only** in:

- `/home/yash/.local/share/passwords/login.txt`
- `/home/yash/.local/share/passwords/master-password.txt`

Both are owner-only files, outside Git. The master password is not stored in a
Kubernetes Secret or in this repository. Do not commit credentials or vault exports.

The initial import used the official Bitwarden CLI, which encrypted the data
before uploading it. Eight login entries and ten explicit missing-credential
notes were imported into the **Homelab** folder. A sync/decrypt round trip verified
all imported password values without logging them. No plaintext import file was
written. The service credentials were not changed.

Recoverable credentials came from current service Secrets and the private dashboard
login record. Source provenance and verification status are included in each item.
Configured Grafana, Nextcloud, and Supabase credentials are labelled unverified
unless their current login was independently checked. Argo CD's initial password
failed comparison with the current password hash, so it was not represented as a
working login. Application password hashes cannot recover the original passwords.

See `/home/yash/.local/share/passwords/inventory-report.json` for the non-secret
inventory and remaining credentials. Missing passwords can be added directly to
the vault; do not reset other services merely to populate the manager.

## Isolation and publication

Data lives on node `boii` under `/home/yash/.local/share/passwords/data`, mounted
at `/data`. Vaultwarden runs as UID/GID 1000 without privileges, host sockets,
service-account tokens, or access to other application data. The directory is 0700.
Vault items are encrypted by the client; account metadata remains server-readable.

Public signups and user invitations are disabled. The admin interface is blocked
by the public gateway, including through the Traefik ingress. Its maintenance token
is Argon2id-hashed in a SealedSecret; the raw maintenance token is owner-only at
`/home/yash/.local/share/passwords/admin-token.txt`. Do not expose this token or add
an admin URL to the public dashboard. Administrative access requires a temporary
127.0.0.1-only port-forward directly to the backend port 8080.

Cloudflare Tunnel `passwords-homelab` routes only this hostname to the authenticated
Vaultwarden application. The existing tunnels and host services are not restarted.
Vaultwarden's own authentication is used so Bitwarden clients remain compatible.
No extra HTTP Basic Auth is inserted into the Bitwarden API path.

## Backups

A Kubernetes CronJob takes a consistent SQLite online backup every day at 03:15
Asia/Kolkata, without stopping Vaultwarden. It also archives the server RSA key
and attachments. The archive is verified for SQLite integrity and required files.
Archives are owner-only under `/home/yash/.local/share/passwords/backups`.
The master password and CLI authentication state are deliberately excluded.
Attachment copying is best-effort if an attachment changes during backup.

Backups are local to the same laptop, with no off-host replica configured. They
are not automatically deleted; monitor capacity and copy archives to independent
storage. Backups contain encrypted vault items but also private metadata and the
server signing key, so treat them as sensitive. Restore requires the master
password; the server does not recover it for the owner.

For recovery, restore a verified archive into a separate empty data directory,
check ownership and SQLite integrity, and point a dedicated recovery deployment
at it. Do not overwrite live data or interrupt other services as a recovery test.
The single-node hostPath design has no failover.

## GitOps

`argocd/passwords-application.yaml` manages this directory with self-heal enabled
and pruning disabled. Bootstrap scripts, passwords, login sessions, decrypted
exports, and recovery archives never belong in this Git directory.
