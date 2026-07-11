# Troubleshooting: Pods Stuck in `CreateContainerError` After K3s Restart

## Symptoms

- Multiple pods stuck in `CreateContainerError`
- Events show:

```text
Error: failed to reserve container name ...
```

- Node is `Ready`
- CPU, Memory, and Disk are healthy

## Root Cause

After an unexpected K3s/containerd restart, stale container metadata remained in containerd, preventing Kubernetes from creating new containers.

## Diagnosis

Check pod events:

```bash
kubectl describe pod -n <namespace> <pod-name>
```

Look for:

```text
failed to reserve container name
```

List exited containers:

```bash
sudo k3s crictl ps -a
```

## Resolution

Remove all exited containers:

```bash
sudo k3s crictl rm $(sudo k3s crictl ps -a -q)
```

Restart K3s:

```bash
sudo systemctl restart k3s
```

Verify:

```bash
kubectl get pods -A
```

## Notes

- PVCs and application data are **not affected**.
- If you see:

```text
Failed to allocate directory watch: Too many open files
```

increase the system's `inotify`/file descriptor limits separately, as it is unrelated to the containerd issue.
