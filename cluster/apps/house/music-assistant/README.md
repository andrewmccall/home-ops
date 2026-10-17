# Music Assistant networking

Music Assistant uses the node's network namespace (`hostNetwork: true`) so it can
send and receive LAN multicast for Spotify Connect, AirPlay, Cast and other player
discovery. `ClusterFirstWithHostNet` retains Kubernetes DNS. The existing ClusterIP
Service, internal Ingress and data PVC remain in use. Its listeners also bind the
node's addresses, so their ports must be available on the node; run one replica.

BGP routes make the pod and Service IP ranges reachable by unicast. They do not
carry link-local mDNS discovery (`224.0.0.251:5353`). An HTTP ingress cannot relay
it either. The Avahi deployment in this repository has only a pod interface and
therefore does not connect the pod network to the physical LAN. Moving this
application to host networking avoids relying on that reflector. Across physical
VLANs, discovery still needs an appropriate mDNS gateway and reachable advertised
addresses; BGP alone does not provide that. Music Assistant's upstream guidance
requires the server and players on the same network.

See the official [installation](https://www.music-assistant.io/get-started/) and
[networking](https://www.music-assistant.io/faq/networking/) guides.

## Spotify setup

These are separate capabilities:

- **Spotify music source:** imports the account's library and lets Music Assistant
  play Spotify content. Complete the playback authorisation step as well as the
  browser login. Soloist temporarily advertises **Music Assistant Pairing**; use
  the same account in the Spotify app, play something and select that device.
- **Spotify Connect plugin:** exposes Music Assistant players in the Spotify app.
  Add it under **Settings → Plugins**, then open its settings and select the
  **Connected players**. The current plugin is added once, with multiple players
  selected in its configuration. Each selected player gets its own advertisement.

A successful music-source login does not configure the Connect plugin. See the
[Spotify source](https://www.music-assistant.io/music-providers/spotify/) and
[Spotify Connect](https://www.music-assistant.io/plugins/spotify-connect/) guides.

For a discovery check from a Mac on the same LAN, run:

```sh
dns-sd -B _spotify-connect._tcp local.
# Stop with Ctrl-C. Resolve an advertised device to check its address and port:
dns-sd -L 'DEVICE NAME' _spotify-connect._tcp local.
```

Only expect a pairing advertisement while its setup flow is active. Permanent
Connect advertisements require a configured plugin and selected available players.
