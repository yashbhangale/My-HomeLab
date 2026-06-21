# Homelab Documentation

A self-hosted homelab running on K3s, exposed to the internet through a
Cloudflare Tunnel, with secure admin access over Tailscale.

Everything you need to understand, operate, and extend this homelab is in this
single document.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Infrastructure Components](#infrastructure-components)
3. [Services](#services)
4. [How Traffic Flows](#how-traffic-flows)
5. [Shared Media Library](#shared-media-library)
6. [Cloudflare Tunnel Configuration](#cloudflare-tunnel-configuration)
7. [GitOps with ArgoCD](#gitops-with-argocd)
8. [Secrets Management (Sealed Secrets)](#secrets-management-sealed-secrets)
9. [Pushing to GitHub](#pushing-to-github)
10. [Adding a New App (Full Playbook)](#adding-a-new-app-full-playbook)
11. [Kasm Workspaces Notes](#kasm-workspaces-notes)
12. [Mobile / Remote Admin via Tailscale](#mobile--remote-admin-via-tailscale)
13. [Common Commands](#common-commands)
14. [Troubleshooting](#troubleshooting)
15. [Security Notes](#security-notes)
16. [Future Improvements](#future-improvements)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                            Internet                              │
│                                                                  │
│   ┌──────────────────┐              ┌──────────────────┐         │
│   │  Cloudflare DNS  │              │   Tailscale VPN  │         │
│   │ (*.yashbhangale  │              │  (kubectl / SSH  │         │
│   │      .site)      │              │   admin access)  │         │
│   └────────┬─────────┘              └────────┬─────────┘         │
│            │                                 │                    │
│            ▼                                 ▼                    │
│   ┌──────────────────┐              ┌──────────────────┐         │
│   │ Cloudflare Tunnel│              │  K3s API :6443   │         │
│   │  (cloudflared    │              │  (Tailscale IP)  │         │
│   │   K8s pod)       │              └──────────────────┘         │
│   └────────┬─────────┘                                           │
│            │ routes by hostname                                  │
│            ▼                                                     │
│   ┌──────────────────────────────────────────────────────────┐ │
│   │                    K3s Cluster (node: boii)              │ │
│   │                                                          │ │
│   │  HomeAssistant  Nextcloud  OpenWebUI  Jellyfin  Kavita   │ │
│   │  Paperless-ngx  Kasm       Filebrowser  ArgoCD           │ │
│   │                                                          │ │
│   │  GitOps: ArgoCD ← Git repo   Secrets: Sealed Secrets     │ │
│   │            Shared media: /srv/media (hostPath)           │ │
│   └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## Infrastructure Components

### Kubernetes (K3s)
- **Distribution**: K3s `v1.35.5+k3s1`
- **Node**: `boii` (single node, control-plane)
- **LAN IP**: `192.168.0.152`
- **API Port**: `6443`
- **Host OS**: Ubuntu 25.10
- **Hardware**: AMD Ryzen 5 4600H (12 threads), Radeon graphics (NO NVIDIA GPU), ~15.5 GB RAM
- **Storage class**: `local-path` (default, `WaitForFirstConsumer`)

### Traefik
- Bundled K3s ingress controller, class name `traefik`.
- Per-app `ingress.yaml` files exist for completeness, but **active hostname
  routing is done by cloudflared**, not Traefik.

### Cloudflare Tunnel (cloudflared)
- Runs as a **K8s pod** in the `cloudflared` namespace (migrated off systemd so
  it survives node IP changes).
- Tunnel ID: `f5d445db-9f0b-47f0-90b8-e344cb5f3325`
- Routes hostnames to in-cluster service DNS names (see config below).

### Tailscale VPN
- Used for secure admin access (kubectl/SSH) to the node and the K3s API,
  without exposing the control plane to the internet.
- Node Tailscale IP: `100.111.171.112`

### ArgoCD (GitOps)
- Deployed via Helm (chart `argo-cd-9.6.0`, app `v3.4.4`) in the `argocd`
  namespace.
- Continuously syncs this Git repo's manifests to the cluster.
- UI: https://argocd.yashbhangale.site
- Config in `argocd/` (`namespace.yaml`, `values.yaml`).

### Sealed Secrets
- Bitnami `sealed-secrets-controller` runs in `kube-system`.
- Encrypts secrets so they can be committed to Git safely. Only the controller
  in the cluster can decrypt them.
- Used for the cloudflared tunnel credentials
  (`cloudflared/sealed-secret.yaml`).

---

## Services

| # | Service | URL | Port | Namespace | Storage | Notes |
|---|---------|-----|------|-----------|---------|-------|
| 1 | Home Assistant | https://ha.yashbhangale.site | 8123 | homeassistant | 10Gi | Home automation |
| 2 | Nextcloud | https://nextcloud.yashbhangale.site | 8080 | nextcloud | 20Gi + shared media (RW) | Helm chart; writes the shared media library |
| 3 | Open WebUI | https://openui.yashbhangale.site | 80 | openwebui | 10Gi | LLM UI; `OLLAMA_BASE_URL=http://192.168.0.107:11434` |
| 4 | Jellyfin | https://jellyfin.yashbhangale.site | 8096 | jellyfin | 5Gi config + 50Gi media + shared media (RO) | Movies/TV/music |
| 5 | Kavita | https://kavita.yashbhangale.site | 5000 | kavita | 2Gi config + 20Gi library + shared media (RO) | Books/comics/manga |
| 6 | Paperless-ngx | https://paperless.yashbhangale.site | 8000 | paperless | 5Gi data + 20Gi media + 2Gi consume | Needs Redis; see note below |
| 7 | Kasm Workspaces | https://kasm.yashbhangale.site | 443 | kasm | 30Gi `/opt` + shared media (RW) | Privileged DinD; 6Gi mem; see notes |
| 8 | Filebrowser | https://files.yashbhangale.site | 80 | filebrowser | 1Gi config + shared media (RW) | Web file manager for `/srv/media` |
| 9 | ArgoCD | https://argocd.yashbhangale.site | 80 | argocd | n/a (Helm) | GitOps continuous delivery |

**Paperless note:** K8s auto-injects a `PAPERLESS_PORT=tcp://<ip>:8000` service
env var that collides with paperless-ngx's own bind-port variable. Fixed by
explicitly setting `PAPERLESS_PORT: "8000"` in its deployment. It also runs a
companion `paperless-redis` Deployment + Service + PVC in the same namespace.

---

## How Traffic Flows

```
Browser (https://app.yashbhangale.site)
   │  HTTPS
   ▼
Cloudflare Edge (TLS, WAF, DDoS)
   │
   ▼
Cloudflare Tunnel (cloudflared pod)
   │  routes by hostname using cloudflared/configmap.yaml
   ▼
K8s Service  (app.<namespace>.svc.cluster.local:<port>)
   │
   ▼
Pod (the app container)
```

**Two things must BOTH exist for a hostname to work:**
1. A **route** in `cloudflared/configmap.yaml` (hostname → K8s service).
2. A **DNS CNAME** in Cloudflare pointing the hostname at the tunnel.

If either is missing, the site is unreachable. Most "site down" issues are one
of these two being absent.

---

## Shared Media Library

A single folder on the node, `/srv/media`, is shared across apps so you upload
once and read everywhere.

```
/srv/media/
├── movies/   ┐
├── tv/       ├─ Jellyfin reads (read-only)
├── music/    ┘
├── books/    ┐
└── comics/   ┴─ Kavita reads (read-only)
```

**Who mounts it:**

| App | Mount path in pod | Access | Purpose |
|-----|-------------------|--------|---------|
| Nextcloud | `/media` | RW | Upload files (via External Storage app) |
| Filebrowser | `/srv` | RW | Web file manager to organize everything |
| Kasm | `/srv/media` | RW | Chrome downloads land here (via Volume Mapping) |
| Jellyfin | `/shared` | RO | Reads movies/tv/music |
| Kavita | `/shared` | RO | Reads books/comics |

**Implementation:** each namespace has its own `hostPath` PV + PVC
(`storageClassName: shared-media`) all pointing at `/srv/media`. Manifests live
in `shared-media/`. This works because it's a single node.

**Permissions:** `/srv/media` is `2777` (group-writable + setgid). Owner is
uid 33 (Nextcloud www-data). Kasm sessions run as uid 1000; the setgid + 0777
bits let all writers cooperate.

### Adding media

- **Nextcloud**: enable External Storage (`php occ app:enable files_external`),
  then add a Local mount pointing at `/media`. Upload through the web/mobile UI.
- **Filebrowser**: just drag/drop and organize at https://files.yashbhangale.site.
- **Kasm Chrome**: set Chrome's download dir to `/home/kasm-user/Downloads/media`
  (requires the Volume Mapping in Kasm — see Kasm notes).

### Kavita requirement (important)

Kavita does **not** allow loose files at a library root. Every book must be in
its **own subfolder**:

```
/srv/media/books/Some Book Title/book.epub      ✅
/srv/media/books/book.epub                       ❌ ("files at root" error)
```

After adding/moving files, in Kavita: library → ⋯ → **Scan Library**
(or **Force Scan** in library settings).

---

## Cloudflare Tunnel Configuration

Defined in `cloudflared/configmap.yaml` (namespace `cloudflared`). Current routes:

```yaml
tunnel: f5d445db-9f0b-47f0-90b8-e344cb5f3325
credentials-file: /etc/cloudflared/credentials/credentials.json

ingress:
  - hostname: nextcloud.yashbhangale.site
    service: http://nextcloud.nextcloud.svc.cluster.local:8080
  - hostname: openui.yashbhangale.site
    service: http://openwebui-open-webui.openwebui.svc.cluster.local:80
  - hostname: ha.yashbhangale.site
    service: http://homeassistant.homeassistant.svc.cluster.local:8123
  - hostname: jellyfin.yashbhangale.site
    service: http://jellyfin.jellyfin.svc.cluster.local:8096
  - hostname: kavita.yashbhangale.site
    service: http://kavita.kavita.svc.cluster.local:5000
  - hostname: paperless.yashbhangale.site
    service: http://paperless.paperless.svc.cluster.local:8000
  - hostname: kasm.yashbhangale.site
    service: https://kasm.kasm.svc.cluster.local:443   # self-signed cert
    originRequest:
      noTLSVerify: true
  - hostname: files.yashbhangale.site
    service: http://filebrowser.filebrowser.svc.cluster.local:80
  - hostname: argocd.yashbhangale.site
    service: http://argocd-server.argocd.svc.cluster.local:80
  - service: http_status:404   # catch-all
```

Service DNS format: `<service-name>.<namespace>.svc.cluster.local:<port>`

After editing the configmap:
```bash
kubectl apply -f cloudflared/configmap.yaml
kubectl rollout restart deployment/cloudflared -n cloudflared
```

---

## GitOps with ArgoCD

ArgoCD watches this Git repository and keeps the cluster in sync with the
manifests here. Push a change → ArgoCD applies it. This is the source of truth
for the cluster.

- **UI**: https://argocd.yashbhangale.site
- **Namespace**: `argocd`
- **Install**: Helm chart `argo-cd-9.6.0` (app `v3.4.4`)
- **Config**: `argocd/values.yaml` runs the server in `insecure` mode
  (`server.insecure: true`) with a `ClusterIP` service, since TLS is terminated
  at the Cloudflare edge and the tunnel handles the HTTPS hop.

### Get the initial admin password
```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo
```
Log in as `admin`. Change the password from the UI after first login, then you
can delete the initial secret.

### Reinstall / upgrade ArgoCD
```bash
helm repo add argo https://argoproj.github.io/argo-helm
kubectl apply -f argocd/namespace.yaml
helm upgrade --install argocd argo/argo-cd -n argocd -f argocd/values.yaml
```

### Point ArgoCD at this repo
Create an `Application` (via UI or CLI) with:
- **Repo URL**: your GitHub repo
- **Path**: the folder to sync (e.g. `jellyfin/`, or a root that contains all
  app folders)
- **Destination**: `https://kubernetes.default.svc`, the matching namespace
- **Sync policy**: automated (with prune + self-heal) once you trust it

Because secrets are sealed (next section), the entire repo — including the
encrypted credentials — is safe for ArgoCD to apply directly from Git.

---

## Secrets Management (Sealed Secrets)

Plaintext Kubernetes Secrets must **never** be committed to Git. This repo uses
Bitnami **Sealed Secrets**: a controller in the cluster holds a private key and
is the only thing that can decrypt a `SealedSecret`. The encrypted file is safe
to commit publicly.

- **Controller**: `sealed-secrets-controller` in `kube-system`
- **Example**: `cloudflared/sealed-secret.yaml` (the tunnel credentials)
- The old plaintext `cloudflared/secret.yaml` has been **removed** from the repo.

### Workflow: seal a new secret
```bash
# 1. Create a normal secret locally (do NOT commit this file)
kubectl create secret generic my-secret \
  --namespace my-ns \
  --from-literal=key=value \
  --dry-run=client -o yaml > /tmp/my-secret.yaml

# 2. Seal it with kubeseal (encrypts using the controller's public key)
kubeseal --controller-namespace kube-system \
  --format yaml < /tmp/my-secret.yaml > my-ns/sealed-secret.yaml

# 3. Commit ONLY the sealed file; delete the plaintext
rm /tmp/my-secret.yaml
git add my-ns/sealed-secret.yaml

# 4. Apply (or let ArgoCD apply it). The controller decrypts it into a
#    real Secret in the cluster.
kubectl apply -f my-ns/sealed-secret.yaml
```

A `SealedSecret` only contains `encryptedData` (ciphertext) — see
`cloudflared/sealed-secret.yaml`. Safe to push.

> ⚠️ Back up the controller's private key. If you lose it, you can't decrypt any
> sealed secret:
> `kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml > sealed-secrets-key-backup.yaml`
> (Store this backup somewhere private — NOT in this repo.)

---

## Pushing to GitHub

### Safe to push ✅
- All `*/namespace.yaml`, `deployment.yaml`, `service.yaml`, `ingress.yaml`,
  `pvc.yaml`
- `cloudflared/configmap.yaml` — contains the tunnel ID (not a secret; it's not
  usable without the credentials)
- `cloudflared/sealed-secret.yaml` — encrypted, safe
- `*/values.yaml` (Helm values), `shared-media/*`, `README.md`

### Do NOT push ❌
- `cloudflared/secret.yaml` (plaintext credentials) — already removed; keep it
  gone. Use the sealed version instead.
- The sealed-secrets controller **private key** backup
- Any `*.deb` / large binaries (e.g. the old `cloudflared-linux-amd64.deb`,
  already removed) — these don't belong in Git
- Local kubeconfig, tokens, `cert.pem`, `*.key`, `.env` files
- Anything under `~/.cloudflared/` or `/etc/cloudflared/`

### Recommended `.gitignore`
There is currently **no `.gitignore`**. Add one before the first push to prevent
accidents:

```gitignore
# Plaintext secrets - never commit
secret.yaml
**/secret.yaml
*.key
cert.pem
*.pem
.env

# Sealed-secrets controller private key backups
sealed-secrets-key*.yaml

# Binaries / archives
*.deb
*.tar
*.tar.gz
*.zip

# Local tooling
kubeconfig
*.kubeconfig
```

> Note: `**/secret.yaml` would also ignore a sealed file if you named it
> `secret.yaml`. The sealed file here is `sealed-secret.yaml`, so it's fine.

### First push
```bash
git status                 # review exactly what will be committed
git add .
git status                 # confirm no secret.yaml / .deb / keys are staged
git commit -m "Homelab K3s manifests: apps, tunnel, sealed secrets, ArgoCD"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Before committing, double-check nothing sensitive is staged:
```bash
git status --porcelain | grep -iE 'secret\.yaml|\.deb|\.key|cert\.pem|\.env' \
  && echo "STOP: sensitive file staged" || echo "OK: nothing sensitive staged"
```

---

## Adding a New App (Full Playbook)

This is the exact, repeatable process used for Jellyfin, Kavita, Paperless,
Kasm, and Filebrowser.

### Step 0 — Gather facts
Container image, HTTP port, volumes to persist, extra services (DB/broker),
required env vars. Check the app's official docs.

### Step 1 — Create folder + manifests
```bash
mkdir -p /home/yash/homelab/<app>
```
Create 5 files (replace `APP`/`PORT`/image/mounts):

**namespace.yaml**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: APP
```

**pvc.yaml**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: APP-config
  namespace: APP
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 5Gi
```

**deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: APP
  namespace: APP
spec:
  replicas: 1
  selector:
    matchLabels:
      app: APP
  template:
    metadata:
      labels:
        app: APP
    spec:
      containers:
      - name: APP
        image: ORG/APP:latest
        ports:
        - containerPort: PORT
        env:
        - name: TZ
          value: "Asia/Kolkata"
        volumeMounts:
        - mountPath: /config
          name: config
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: APP-config
```

**service.yaml**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: APP
  namespace: APP
spec:
  selector:
    app: APP
  ports:
  - port: PORT
    targetPort: PORT
  type: ClusterIP
```

**ingress.yaml** (kept for completeness; cloudflared does real routing)
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: APP
  namespace: APP
spec:
  ingressClassName: traefik
  rules:
  - host: APP.yashbhangale.site
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: APP
            port:
              number: PORT
```

### Step 2 — Validate
```bash
kubectl apply --dry-run=client -f <app>/
```

### Step 3 — Apply
```bash
kubectl apply -f <app>/
```
> ⚠️ **Namespace race:** if you see `namespaces "<app>" not found`, just run the
> same `kubectl apply` a second time (the namespace exists by then). To avoid
> it, apply `namespace.yaml` first.

### Step 4 — Add the tunnel route
Edit `cloudflared/configmap.yaml`, add a block **above** the `http_status:404`:
```yaml
- hostname: APP.yashbhangale.site
  service: http://APP.APP.svc.cluster.local:PORT
```
Then:
```bash
kubectl apply -f cloudflared/configmap.yaml
kubectl rollout restart deployment/cloudflared -n cloudflared
```

### Step 5 — Create DNS
```bash
cloudflared tunnel route dns f5d445db-9f0b-47f0-90b8-e344cb5f3325 APP.yashbhangale.site
```
(Or in Cloudflare dashboard: add a **CNAME** `APP` →
`f5d445db-9f0b-47f0-90b8-e344cb5f3325.cfargotunnel.com`, Proxied.)

### Step 6 — Verify
```bash
kubectl get pods -n <app>
kubectl rollout status deployment/<app> -n <app> --timeout=120s
curl -s -o /dev/null -w "%{http_code}\n" https://APP.yashbhangale.site/
```
`200`/`301`/`302` = working. `000` usually = DNS still propagating, retry.

### Apps that need a database/broker
Add an extra manifest (e.g. `redis.yaml`) with the DB's Deployment + Service +
PVC in the same namespace, and point the app at it via its in-cluster DNS name,
e.g. `redis://APP-redis.APP.svc.cluster.local:6379`.

### Mounting the shared media library
Add a PV/PVC in `shared-media/<app>-media-pv.yaml` (copy an existing one,
change names/labels and `accessModes`: `ReadOnlyMany` for readers,
`ReadWriteOnce` for writers), then add a `volumeMounts` + `volumes` entry to the
deployment referencing `claimName: <app>-shared-media`.

---

## Kasm Workspaces Notes

Browser-based streaming desktops/apps, deployed as a single **privileged**
Docker-in-Docker container (`lscr.io/linuxserver/kasm:latest`).

- 6Gi memory limit, 30Gi `/opt` PVC, ports 443 (app) + 3000 (setup wizard),
  both HTTPS self-signed.

### First-time setup
The app on 443 doesn't serve until the wizard (port 3000) is completed; until
then the public URL returns 502 (expected). To do setup, temporarily point the
tunnel at port 3000 **or** port-forward:
```bash
kubectl port-forward -n kasm svc/kasm 3000:3000 --address 0.0.0.0
# then open https://192.168.0.152:3000  (accept self-signed cert)
```
Default users: `admin@kasm.local` / `user@kasm.local`. After setup, switch the
tunnel route back to 443.

### Behind a reverse proxy (required)
Admin UI → **Infrastructure → Zones → default zone → Proxy Port = 0**, or
Workspace sessions won't launch.

### No NVIDIA GPU — disable GPU on workspaces
This host has AMD Radeon graphics, no NVIDIA GPU. If a workspace was configured
with a GPU/nvidia runtime, sessions fail with
`failed to initialize NVML: ERROR_LIBRARY_NOT_FOUND`. Fix: clear the NVIDIA
`run_config` on each workspace (set GPUs to 0 in the admin UI). It was cleared
directly in the DB once with:
```bash
kubectl exec -n kasm deploy/kasm -- sh -c \
  'docker exec kasm_db psql -U kasmapp -d kasm -c "UPDATE images SET run_config = '"'"'{}'"'"';"'
```

### Downloads → shared media
Shared media is mounted into the Kasm pod at `/srv/media`. To get it into a
Chrome **session** (a separate inner container), add a **Volume Mapping** in the
admin UI (Workspaces → edit Chrome → Volume Mapping):
```json
{
  "/srv/media": {
    "bind": "/home/kasm-user/Downloads/media",
    "mode": "rw", "uid": 1000, "gid": 1000, "required": true
  }
}
```
Then set Chrome's download location to `/home/kasm-user/Downloads/media`.

---

## Mobile / Remote Admin via Tailscale

Goal: manage K3s from an iPad/phone without exposing the API to the internet.

- K3s API: `https://100.111.171.112:6443` (Tailscale IP)
- Auth: Bearer token; enable "Skip Endpoint TLS Verification" in the mobile app
  (or add the Tailscale IP to the cert SAN, below).

**The gotcha:** the API server cert didn't include the Tailscale IP in its SAN,
causing `CERTIFICATE_VERIFY_FAILED`. Fix by adding it to K3s config:

`/etc/rancher/k3s/config.yaml`
```yaml
tls-san:
  - 100.111.171.112
  - boii.tailnet.ts.net   # optional, if using MagicDNS
```
Restart K3s, then verify:
```bash
sudo openssl x509 -in /var/lib/rancher/k3s/server/tls/serving-kube-apiserver.crt \
  -text -noout | grep -A1 "Subject Alternative Name"
```

**Optional read-only mobile account:**
```bash
kubectl create serviceaccount ipad-viewer -n kube-system
kubectl create clusterrolebinding ipad-viewer \
  --clusterrole=view --serviceaccount=kube-system:ipad-viewer
kubectl create token ipad-viewer -n kube-system
```

Cloudflare Tunnel is NOT used for K8s API access — it's dedicated to app ingress.

---

## Common Commands

```bash
# Pods / services across an app
kubectl get pods -n <namespace>
kubectl get svc  -n <namespace>

# Logs
kubectl logs -n <namespace> -l app=<app> --tail=50 -f

# Restart a deployment
kubectl rollout restart deployment/<app> -n <namespace>
kubectl rollout status  deployment/<app> -n <namespace> --timeout=120s

# Cloudflared (after route changes)
kubectl apply -f cloudflared/configmap.yaml
kubectl rollout restart deployment/cloudflared -n cloudflared
kubectl logs -n cloudflared -l app=cloudflared --tail=30

# Create a DNS route for a new hostname
cloudflared tunnel route dns f5d445db-9f0b-47f0-90b8-e344cb5f3325 <host>.yashbhangale.site

# Test a public URL end-to-end
curl -s -o /dev/null -w "%{http_code}\n" https://<host>.yashbhangale.site/

# PVC status
kubectl get pvc -A

# Port-forward for local debugging
kubectl port-forward -n <namespace> svc/<svc> <local>:<remote>
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Pod `Pending`, PVC `Pending` | `local-path-provisioner` unhealthy | `kubectl get pods -n kube-system \| grep local-path`, check its logs (it once crashed with "no route to host" to the API) |
| `namespaces "<app>" not found` on apply | namespace race | Re-run the same `kubectl apply` |
| Public URL `502` | origin pod not ready/crashing, or app not serving yet (e.g. Kasm pre-wizard) | `kubectl logs -n <app> -l app=<app>` |
| Public URL `000` / `404` | missing DNS CNAME or tunnel route | Re-check tunnel config + `cloudflared tunnel route dns` |
| cloudflared logs "Unable to reach origin" | wrong service DNS/port in configmap | Verify `kubectl get svc -n <app>` matches the route |
| App env var clobbered (e.g. `*_PORT=tcp://...`) | K8s injects `<SVC>_PORT` service-discovery var that collides with the app's own var | Set the var explicitly in the deployment (see Paperless) |
| Kasm session fails: `NVML ERROR_LIBRARY_NOT_FOUND` | GPU/nvidia runtime enabled but no NVIDIA GPU | Clear workspace `run_config`/disable GPU (see Kasm notes) |
| Kavita: "files at root" error | loose file in library root | Put each book in its own subfolder, then Scan |
| Filebrowser `admin/admin` rejected | `s6` image generates a random password on first boot | Read it from the pod logs: `kubectl logs -n filebrowser -l app=filebrowser \| grep -i password` |
| Mobile kubectl `CERTIFICATE_VERIFY_FAILED` | Tailscale IP not in API cert SAN | Add to `tls-san` in K3s config, restart |

---

## Security Notes

- All external traffic goes through Cloudflare (WAF, DDoS); TLS terminates at
  Cloudflare's edge.
- Admin access (kubectl/SSH/API) is via Tailscale only — no port forwarding on
  the router.
- **Internet-exposed apps rely on their own login** (no extra auth layer in
  front). Change all default passwords immediately — especially Filebrowser.
- **Kasm runs privileged** (Docker-in-Docker). This grants near-host-level
  access on the node; it's isolated in its own namespace but has a larger blast
  radius than other apps. Acceptable for a single-node homelab.
- For first-run wizards exposed publicly (e.g. Kasm on 3000), don't leave them
  exposed longer than needed.

---

## Future Improvements

- **Static DHCP reservation** for the node so `192.168.0.152` never changes.
- **Monitoring**: Prometheus + Grafana (the `prometheus-community` Helm repo is
  already added).
- **Logging**: Loki + Grafana.
- **Backups**: Velero for K8s resources; regular `/srv/media` and PVC backups.
- **External database** for Nextcloud and Paperless (Postgres) instead of
  SQLite for better performance.
- **MagicDNS** hostname for the K3s API instead of the raw Tailscale IP.
- **GPU acceleration** for Jellyfin/Kasm via AMD `/dev/dri` (VAAPI) — supported
  by this hardware, unlike the NVIDIA path.
```
