#!/bin/sh
# s6 executes cont-init scripts as root before Hermes starts.  The gateway and
# terminal tool run as `hermes`, so key material created during image builds or
# maintenance must be handed back to that unprivileged account on every boot.
set -eu

# HERMES_HOME is injected only when the gateway service starts; cont-init runs
# earlier, so use the image's canonical persistent state mount directly.
state_dir="/opt/data/nimbox-sre"
install -d -m 700 -o hermes -g hermes "$state_dir"

if [ -f "$state_dir/agent_ed25519" ]; then
    chown hermes:hermes "$state_dir/agent_ed25519"
    chmod 600 "$state_dir/agent_ed25519"
fi

if [ -f "$state_dir/agent_ed25519.pub" ]; then
    chown hermes:hermes "$state_dir/agent_ed25519.pub"
    chmod 644 "$state_dir/agent_ed25519.pub"
fi

for file in "$state_dir/ticket-secrets.json" "$state_dir/known_hosts"; do
    if [ -f "$file" ]; then
        chown hermes:hermes "$file"
        chmod 600 "$file"
    fi
done
