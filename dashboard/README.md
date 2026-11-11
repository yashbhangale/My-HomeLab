# Homelab dashboard

- **Homepage:** https://dashboard.yashbhangale.site
- **Gatus uptime history:** https://status.yashbhangale.site
- **Login:** `/home/yash/.local/share/homelab-dashboard/login.txt` (owner-only, outside Git).

Homepage v2.7.0 provides the application launcher and Kubernetes resource status.
Gatus v5.38.0 checks 15 applications and five infrastructure endpoints every minute.
The existing Prometheus supplies 16 host/cluster metrics, refreshed every 15 seconds;
Grafana remains the destination for detailed time-series exploration.

## Configuration

Edit `generate.py`, then run `python3 dashboard/generate.py` from the repository root.
This generates `config.yaml`. After changing the ConfigMap, roll out **only** the
`dashboard/homepage` deployment to copy the seed files into its writable config.
Do not restart shared networking, monitoring, Cloudflare, or the host.

The native Homepage components, slate palette, dark theme, and responsive layout
are retained. Configuration groups the live telemetry first, then app categories,
then operations and uptime. All reported values come from live sources.

Each application card selects its actual namespace/pod labels and shows pod CPU/RAM.
Additional applications can be added to `APPS`, or discovered using opt-in
`gethomepage.dev/*` Ingress annotations. No existing application manifests are
modified just to add dashboard annotations.

## Security and data

All public pages and API requests pass through a bcrypt-authenticated gateway.
Both hostnames have a separate login from Obsidian. Secrets are committed only as
cluster-specific SealedSecrets. The new named tunnel `dashboard-homelab` is isolated
from the pre-existing homelab and Obsidian tunnels.

The Homepage service account can only get/list namespaces, pods, nodes, ingresses,
and resource metrics; it cannot read Secrets, execute commands, or change workloads.
Only Homepage receives a projected, short-lived service-account token. No Docker
socket, host filesystem, or host credentials are mounted into Homepage.

Gatus persists SQLite history at `/home/yash/.local/share/homelab-dashboard/gatus`
on node `boii`. Back it up to preserve history. The deployment is node-local and
single-replica; Kubernetes does not back up this directory. Each endpoint retains
1,440 recent check results and 100 events; uptime history starts at deployment.
Configured alerts are visible through Prometheus/Grafana; no email, Slack, or other
outgoing notifications have been enabled by this deployment.

A namespace NetworkPolicy admits the tunnel and Traefik to the authenticated
port only. Homepage's raw port and the internal Gatus API are not exposed through
the Service. Internal health checks test service reachability; pod readiness is
shown separately. Obsidian checks its public authentication challenge (HTTP 401),
which is labelled as gateway reachability rather than a signed-in editor check.

Kasm's in-cluster self-signed certificate is explicitly accepted for its health
check. Supabase's API is checked for its expected unauthenticated HTTP 401 response.
A healthy login screen or API challenge does not prove a signed-in user workflow.

## Deploy

```sh
kubectl apply -f dashboard/
kubectl -n dashboard rollout status deployment/homepage
kubectl -n dashboard rollout status deployment/dashboard-tunnel
```

GitOps application: `argocd/dashboard-application.yaml`, with self-heal enabled and
pruning disabled. A config change is coupled to a pod-template config digest to
roll out only this dashboard when the generated configuration changes.
