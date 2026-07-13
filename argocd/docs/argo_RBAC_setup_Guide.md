# Argo CD RBAC Setup Guide

## Overview

This guide explains how to configure **Role-Based Access Control (RBAC)** in Argo CD using **local user accounts**. The setup creates:

| User     | Role           | Access                                                 |
| -------- | -------------- | ------------------------------------------------------ |
| `admin`  | Built-in Admin | Full access                                            |
| `yash`   | Admin          | Full access                                            |
| `viewer` | Read-only      | View applications, resources, manifests, and logs only |

The `viewer` account can inspect the GitOps environment without being able to modify, synchronize, delete, or create resources.

---

# Prerequisites

* Kubernetes cluster
* Argo CD installed
* `kubectl` configured
* Argo CD CLI (`argocd`) installed

Verify CLI installation:

```bash
argocd version
```

---

# Step 1 — Create Local Accounts

Edit the Argo CD ConfigMap:

```bash
kubectl edit configmap argocd-cm -n argocd
```

Under the `data:` section, add:

```yaml
accounts.yash: login
accounts.viewer: login
```

Example:

```yaml
data:
  admin.enabled: "true"

  accounts.yash: login
  accounts.viewer: login
```

Save and exit.

---

# Step 2 — Configure RBAC Policies

Edit the RBAC ConfigMap:

```bash
kubectl edit configmap argocd-rbac-cm -n argocd
```

Replace the `data:` section with:

```yaml
data:
  policy.csv: |
    # Admin role
    g, yash, role:admin

    # Read-only role permissions
    p, role:readonly, applications, get, */*, allow
    p, role:readonly, applicationsets, get, *, allow
    p, role:readonly, logs, get, */*, allow
    p, role:readonly, projects, get, *, allow
    p, role:readonly, repositories, get, *, allow
    p, role:readonly, clusters, get, *, allow

    # Read-only user
    g, viewer, role:readonly

  policy.default: ""
  policy.matchMode: glob
  scopes: '[groups]'
```

> **Important:** Do **not** grant `exec` permission to read-only users unless terminal access into containers is explicitly required.

---

# Step 3 — Restart Argo CD

Restart the Argo CD server to apply the configuration.

```bash
kubectl rollout restart deployment argocd-server -n argocd
```

Wait until the deployment becomes available:

```bash
kubectl rollout status deployment argocd-server -n argocd
```

---

# Step 4 — Login to Argo CD

If using an Ingress or domain:

```bash
argocd login <ARGOCD_SERVER> --grpc-web
```

Example:

```bash
argocd login argocd.example.com --grpc-web
```

If using a self-signed certificate:

```bash
argocd login argocd.example.com --grpc-web --insecure
```

---

# Step 5 — Set User Passwords

Assign passwords for newly created users.

Admin user:

```bash
argocd account update-password --account yash --grpc-web
```

Viewer user:

```bash
argocd account update-password --account viewer --grpc-web
```

The CLI will prompt for:

* Current admin password
* New password
* Password confirmation

Password requirements:

* Minimum 8 characters
* Maximum 32 characters

---

# Step 6 — Verify Accounts

List available accounts:

```bash
argocd account list --grpc-web
```

Example output:

```text
NAME      ENABLED
admin     true
yash      true
viewer    true
```

---

# Step 7 — Test Permissions

Login using the `viewer` account.

The viewer should be able to:

* View Applications
* View Resources
* View Pods
* View Services
* View Deployments
* View Manifests
* View Logs
* View Health Status
* View Sync Status

The viewer should **not** be able to:

* Sync Applications
* Delete Applications
* Create Applications
* Rollback
* Modify Settings
* Register Clusters
* Add Repositories
* Execute Terminal Sessions

---

# Verifying Access

You can verify the logged-in user:

```bash
argocd account get-user-info --grpc-web
```

---

# Updating RBAC Policies

Whenever RBAC policies are modified:

1. Edit `argocd-rbac-cm`
2. Save the changes
3. Restart the Argo CD server

```bash
kubectl rollout restart deployment argocd-server -n argocd
```

---

# Troubleshooting

## "command not found: argocd"

The Argo CD CLI is not installed.

Verify:

```bash
argocd version
```

---

## "Argo CD server address unspecified"

Login first:

```bash
argocd login <ARGOCD_SERVER> --grpc-web
```

---

## "Failed to invoke grpc call"

Use the `--grpc-web` flag:

```bash
argocd account list --grpc-web
```

---

## "new password does not match expression"

The password must contain between **8 and 32 characters**.

---

## Verify ConfigMaps

```bash
kubectl get configmap argocd-cm -n argocd
kubectl get configmap argocd-rbac-cm -n argocd
```

---

# Final RBAC Model

| Account | Role          | Permissions      |
| ------- | ------------- | ---------------- |
| admin   | Administrator | Full access      |
| yash    | Administrator | Full access      |
| viewer  | Read-only     | View-only access |

This configuration follows the principle of least privilege by allowing administrators to manage the GitOps platform while providing auditors, clients, or team members with safe, read-only visibility into the Argo CD environment.
