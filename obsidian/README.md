# Obsidian browser workspace

URL: https://obsidian.yashbhangale.site

Runs the actual LinuxServer Obsidian desktop through its browser streaming client.
The app image is pinned to the amd64 digest inspected on 2026-11-10.

## Data and login

- Vault: `/home/yash/vault/content` on node `boii`, mounted at `/vault`.
- App profile: `/home/yash/.local/share/obsidian-web/config`, mounted at `/config`.
- Browser edits and local edits use the same files. This is not, by itself,
  Obsidian Sync or automatic GitHub synchronization.
- Open `/vault` as the vault if the app presents its vault picker.
- Private login instructions: `/home/yash/.local/share/obsidian-web/login.txt`
  (owner-only, outside Git).
- Recovery copy taken during deployment:
  `/home/yash/.local/share/obsidian-web/vault-before-web.tar.gz`.
- Host directories must exist with UID/GID 1000 ownership before deploying.
  Data remains in place if the pod is replaced; it is node-local with no failover.
- Back up both the vault and app profile. Kubernetes does not back up hostPath data.

## Routing and security

Cloudflare DNS -> dedicated named tunnel `obsidian-homelab` -> authenticated
Nginx gateway on `obsidian.obsidian.svc.cluster.local:80` -> Obsidian on localhost:3000.
Cloudflare terminates public TLS; the internal HTTP hop is within the cluster.
The gateway checks a bcrypt password hash; Obsidian also receives the matching
CUSTOM_USER/PASSWORD from the Secret. The ingress routes through that gateway too.
The NetworkPolicy permits only the Obsidian connector and Traefik to reach port
8080 and blocks direct incoming access to the streaming backend.

Only the content directory is mounted; host SSH keys, Docker sockets, and Kubernetes
credentials are not provided to the app. The pod has no mounted service account token.
Authentication and tunnel credentials are stored as cluster-specific SealedSecrets.
Rotating the password requires updating both PASSWORD and the bcrypt htpasswd value,
resealing the Secret, and rolling out only the Obsidian deployment.

The existing shared homelab tunnel and its configuration were left untouched.
This dedicated connector avoids restarting a service used by other applications.

## Deployment

```sh
kubectl apply -f obsidian/
kubectl -n obsidian rollout status deployment/obsidian
kubectl -n obsidian rollout status deployment/obsidian-tunnel
```

For recovery on a new cluster, restore host directories, recreate/reseal credentials,
and update the node selector. SealedSecrets are tied to this cluster's sealing key.
DNS points to tunnel `0b6647a4-765a-420b-a9dd-d840b55fe513`.
Do not restart the host or shared infrastructure to validate this application.
