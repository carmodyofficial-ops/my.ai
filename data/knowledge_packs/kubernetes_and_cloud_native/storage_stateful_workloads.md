# Kubernetes Storage and Stateful Workloads

## Storage Objects

- PersistentVolume: cluster storage resource.
- PersistentVolumeClaim: workload request for storage.
- StorageClass: dynamic provisioning policy.
- VolumeMount: container mount point.

## Stateful Troubleshooting

Check:

- PVC is Bound.
- StorageClass exists and supports requested access mode.
- Node can attach/mount the volume.
- StatefulSet has stable identity expectations.
- Backups exist before destructive changes.

## Safety Boundary

Never recommend deleting PVCs, PVs, or StatefulSets with data until backup and impact are confirmed.
