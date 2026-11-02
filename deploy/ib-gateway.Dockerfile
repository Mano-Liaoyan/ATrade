# Image of the Compose service `ib-gateway`: the gnzsnz IB Gateway image and the ATrade watchdog (docs/architecture/ibkr.md 7.4).
# Build context: deploy/ (see deploy/compose.yaml).
# COPY sets the file mode. A bind mount would keep the mode of the server checkout, and a strict umask on the server
# then stops the container user (uid 1000) from reading the script.

# ghcr.io/gnzsnz/ib-gateway:stable (IB Gateway 10.50.1f), pinned by digest.
FROM ghcr.io/gnzsnz/ib-gateway:stable@sha256:1e2236804ac949b789197c225a048c0c891c9958f948c87166226e5b647ff581
COPY --chmod=755 ib-gateway-watchdog.sh /home/ibgateway/atrade-watchdog.sh
