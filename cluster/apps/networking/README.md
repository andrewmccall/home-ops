# Home network discovery and routed pods

Calico peers with the home gateway at `10.0.0.1`. It advertises pod blocks from
`10.42.0.0/16`, Service addresses from `10.43.0.0/16`, and external addresses from
`10.44.0.0/16`. BGP supplies unicast routes; it does not forward mDNS discovery.

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

## Scoped Avahi experiment

Avahi is an mDNS daemon with a reflector that can repeat discovery between
interfaces. The existing `avahi-daemon` deployment has only a normal pod interface,
so it does not provide a LAN-to-pod path.

An isolated host-network Avahi 0.8 relay was tested with exactly two allowed
interfaces: the node LAN interface and one disposable pod's host-side Calico veth.
The veth needed a temporary IPv4 address for Avahi to use it. A Spotify service
filter allowed discovery and address resolution in both directions. Unrelated
Sendspin/SSH services, a negative test service, and an untargeted pod were checked.
Avahi's service filter is not a packet firewall: queries and host-address records
can still pass between those two interfaces.

The temporary relay and its veth address were removed. A permanent relay still
needs pod-replacement reconciliation and real Music Assistant playback verification.
Music Assistant remains on its working host-network configuration meanwhile.
Do not treat discovery alone as proof of working audio or routed connections.
