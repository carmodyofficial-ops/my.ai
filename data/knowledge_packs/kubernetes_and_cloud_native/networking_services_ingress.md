# Kubernetes Networking, Services, and Ingress

## Service Types

- ClusterIP: internal stable service endpoint.
- NodePort: exposes on node ports.
- LoadBalancer: asks cloud/bare-metal integration for an external load balancer.
- ExternalName: DNS alias.

## Debugging Service Reachability

Check:

- Service selector matches Pod labels.
- Endpoints or EndpointSlices contain ready backends.
- Pod readiness gates are passing.
- NetworkPolicy allows traffic.
- DNS resolves expected service name.
- Ingress routes to the correct Service and port.

## Useful Commands

- kubectl get svc
- kubectl describe svc <name>
- kubectl get endpoints <name>
- kubectl get endpointslice
- kubectl get ingress
- kubectl describe ingress <name>
- kubectl exec -it <pod> -- nslookup <service>
- kubectl exec -it <pod> -- curl -v http://<service>:<port>

## LAN Exposure

For local my.ai-style LAN exposure, consider:

- k3s with Traefik or another ingress controller
- NodePort with firewall awareness
- LoadBalancer via MetalLB on bare metal
- reverse proxy in front of the cluster
- authentication before exposing sensitive applications
