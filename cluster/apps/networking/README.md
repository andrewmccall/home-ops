# Networking: routes, DNS, the public tunnel and routed pods

Public hostnames come in through one Cloudflare tunnel to the `external` Gateway
([cloudflared/README.md](cloudflared/README.md)); see "Making a service public" below.

Calico peers with the home gateway at `10.0.0.1`. It advertises pod blocks from
`10.42.0.0/16`, Service addresses from `10.43.0.0/16`, and external addresses from
`10.44.0.0/16`. BGP supplies unicast routes; it does not forward mDNS discovery.

## Routes, Gateways and DNS

Services are reached through two Envoy Gateways in this namespace (`envoy-gateway/`), by
HTTPRoutes (or GRPCRoutes) that sit next to each app, in this repo or another:

| Gateway | Reached from | DNS |
|---|---|---|
| `internal` | The LAN only | `external-dns-unifi`: a LAN record pointing at the Gateway |
| `external` | The LAN, and the internet through the public tunnel (`cloudflared/`) | Also `external-dns-cloudflare`: a proxied public record pointing at the tunnel |

Both listen on 443 with the `*.andrewmccall.com` certificate (`networking/ingress-tls`) and
redirect port 80 to HTTPS. A route attaches with:

```yaml
parentRefs:
  - name: internal          # or external
    namespace: networking
    sectionName: https
hostnames:
  - my-app.${DOMAIN}
```

DNS records follow the routes: add, change or delete a route and its records follow within
a minute. No tunnel or DNS setting needs editing.

### Making a service public

Attaching a route to `external` publishes it on the internet. As a guard, `external` only
accepts routes from namespaces labelled for it, so both are needed:

1. The namespace carries `home-ops.andrewmccall.com/public-routes: "true"`. Labelled now:
   `house` (Home Assistant), `flux-system` (the GitHub webhook) and the game's namespaces
   (labelled in their own repository).
2. The route's `parentRefs` names the `external` Gateway.

Without the label the route is refused, and nothing is published:

```sh
kubectl -n <namespace> get httproute <name> -o jsonpath='{.status.parents[*].conditions[?(@.type=="Accepted")]}'
# "status":"False","reason":"NotAllowedByListeners" -> the namespace lacks the label
```

`GatewayRouteNotAccepted` alerts on any route a Gateway refuses. Before publishing,
decide how the service authenticates: anything on `external` faces the whole internet.

## NetworkPolicies: pods are reachable from the LAN

BGP routes pod addresses to the LAN, so a pod with no NetworkPolicy can be reached
directly from any LAN device, bypassing the Gateways. Every namespace this repo owns
carries a `default` policy (in its `networkpolicy.yaml`) that selects all pods and
admits only:

- the same namespace;
- `monitoring`, for Prometheus scrapes, where the namespace serves metrics;
- the Envoy proxies, where the namespace has routes on a Gateway:

```yaml
- namespaceSelector:
    matchLabels:
      kubernetes.io/metadata.name: networking
  podSelector:
    matchLabels:
      app.kubernetes.io/managed-by: envoy-gateway
      app.kubernetes.io/component: proxy
```

Anything else is an extra named policy beside `default` (policies add up): the Envoy
proxies accept all traffic, OTLP on the collector is open to every namespace, MQTT
admits `house` and `monitoring`, and Home Assistant and Music Assistant admit the LAN
(`${LAN_CIDR}`) for discovery and players. Traffic from the node is always allowed by
Calico, so kubelet probes, API-server webhook calls and `kubectl port-forward` need no
rule. A new namespace copies the `default` pattern; a new app needing LAN access gets
its own policy scoped to its pods. `kube-system`, `calico-system` and `games` have none.

## UniFi asymmetric pod TCP

The node and home clients share `10.0.0.0/23`. A client sends traffic for a pod
through the gateway, while the node normally returns it directly to the client.
UniFi sees only part of the TCP handshake. Its Internal-to-External **Block
Invalid Traffic** policy can then drop subsequent packets. BGP-routed pod
addresses fall under this zone pair in the current configuration.

An isolated HTTP test established this failure: traffic reached the pod, its
SYN-ACK left the node directly, and the final ACK did not reach the node. Sending
only that test pod's replies through the gateway restored HTTP. A temporary
router exception for one client, one pod and one port also restored HTTP.
After the exception was removed and policy propagation settled, HTTP failed again.

The retained router policy is **Allow asymmetric LAN to Kubernetes pods**:

| Match | Value |
|---|---|
| Source | Internal zone, `10.0.0.0/23` |
| Destination | External zone, `10.42.0.0/16` |
| Protocol | IPv4 TCP |
| Connection state | `INVALID` |
| Action | Allow, before the existing invalid-state block |

This permits invalid-state TCP packets only for that LAN-to-pod scope. It does
not distinguish a legitimate asymmetric flow from another packet classified
invalid in the same scope. The current zone policy already allows general LAN
outbound traffic to these addresses. If LAN-to-pod restrictions are introduced,
review this earlier exception alongside them. If the node moves to a separate
transit network and return routing becomes symmetric, remove the exception.

Manage this policy with the supported UniFi Integration API:

```sh
# Read-only plan; --insecure accepts this gateway's self-signed TLS certificate.
python3 scripts/configure-unifi-pod-routing.py --insecure
python3 scripts/configure-unifi-pod-routing.py --apply --insecure
# Roll back only the exact managed policy:
python3 scripts/configure-unifi-pod-routing.py --remove --insecure
```

The helper reads the existing `external-dns-unifi-secret` credential in memory,
requires the home controller and Default site, resolves zone IDs, and checks the
policy's ordering. It saves a local mode-0600 policy snapshot under
`.engineering/unifi-firewall/` before mutation. Reapplying an identical rule makes
no changes. Router policies are outside Flux's Kubernetes inventory; this helper
is their explicit application step. It does not change BGP advertisements.

The official [UniFi policy API](https://developer.ui.com/network/v10.6.106/createfirewallpolicy)
and [zone firewall documentation](https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi)
provide the underlying policy model.

## Scoped Avahi relay

`avahi-relay` runs on `vecna` with host networking. Its controller selects exactly
one local, running, non-host-network pod in `house` bearing the label
`home-ops.andrewmccall.com/mdns-relay=music-assistant`. Avahi sees only `enp5s0`
and that pod's host-side Calico veth. Other pods do not join this discovery path.

The service allowlist is Spotify Connect, Sendspin clients and servers, and Music
Assistant (`_spotify-connect`, `_sendspin`, `_sendspin-server`, `_mass`, all TCP).
Avahi's filter restricts service advertisements; queries and host-address records
can still pass between the two allowed interfaces. It is not a packet firewall.
DLNA uses SSDP and is outside this relay. The configured Rec Room TV DLNA player
will need a separate discovery path before its playback can be relied on after
a pod-network cutover. AirPlay and Chromecast discovery are also outside the list.

The controller polls namespaced pod metadata every three seconds and updates the
interface allowlist after pod replacement. Multiple eligible pods or API errors
stop reflection. Avahi also stops if its controller status goes stale for 25
seconds. No eligible pod is a healthy idle state. Use a single-replica Recreate
Music Assistant deployment to avoid ambiguous targets during updates.

Calico veths normally have no IPv4 address, so the controller adds
`169.254.1.1/32` only to the selected link. It journals ownership and the kernel
interface index in `/run/home-ops-mdns/owned.json`; a reused interface name does
not establish ownership. Removing an interface's last IPv4 address flushes its
link routes, so cleanup journals and restores the existing direct pod route.
It does not create a route where none existed. Pod deletion normally removes
the veth and address together. Keep this Calico-specific behavior under test
when changing CNI or kernel versions.

Avahi runs as UID 86 with no capabilities and no D-Bus access. The controller has
`NET_ADMIN` in the host network namespace and write access to its small host state
directory; that capability can change node networking, despite the controller's
narrow logic. Its projected API token can list/get pods in `house`, cannot read
Secrets, and is mounted only into the controller. Images are pinned by digest.
The host's existing non-reflecting Avahi instance remains separate.

Verification:

```sh
python3 -m unittest discover -s tests -p test_avahi_relay.py
python3 scripts/verify-mdns-relay.py
# During isolated testing, select the labelled MA-image probe instead:
python3 scripts/verify-mdns-relay.py --pod mdns-relay-probe-v3
```

The read-only live check verifies normal pod networking, active relay selection,
Spotify/Sendspin resolution and TCP connectivity, and exclusion of SSH service
discovery. It needs awake LAN devices. It does not prove audible playback.
Disposable-pod replacement, relay replacement, API-access loss and route
preservation were exercised before the production cutover. The unit tests cover
ownership, reused interface names and interrupted route restoration.

The 2026-10-18 cutover put Music Assistant 2.10.7 on normal pod networking.
The UI, routed pod API and advertised Service ports were reachable from the LAN;
Spotify logged in and Satellite1 reconnected over Sendspin. An untargeted Home
Assistant pod received none of the tested discovery services. The user also
confirmed normal audible Spotify playback on the office Satellite1 after cutover.

To roll back a Music Assistant pod-network cutover, restore its
`hostNetwork: true` and `dnsPolicy: ClusterFirstWithHostNet`, then reconcile Flux.
The relay ignores host-network targets. Remove the relay only after returning
Music Assistant to that working configuration, allowing graceful controller
shutdown to clean up its address. This arrangement is specific to this routed
Calico home cluster; Music Assistant's upstream deployment guidance does not
support Kubernetes networking.
