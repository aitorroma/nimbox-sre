FROM nousresearch/hermes-agent:main

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# The gateway runs in Hermes' own virtualenv. Install the plugin dependency
# there (the image-level `uv pip` would otherwise install it for the system
# interpreter and the plugin would fail to import at runtime).
RUN uv pip install --python /opt/hermes/.venv/bin/python --no-cache-dir httpx

# Install the NimBox integration as a Hermes plugin.  Copying standalone
# files into /opt/hermes/tools only registers them; it does not expose their
# toolset.  Plugins are discovered and wired into Hermes automatically.
COPY --chown=hermes:hermes plugins/nimbox_sre/ /opt/hermes/plugins/nimbox_sre/

# Copy skills
COPY --chown=hermes:hermes skills/ /opt/hermes/skills/

# Copy SOUL
COPY --chown=hermes:hermes docker/SOUL.md /opt/hermes/docker/SOUL.md

# Repair ownership of persistent private state before the unprivileged Hermes
# gateway starts. Named Docker volumes can retain files created by root during
# maintenance commands.
COPY docker/ensure-state-permissions.sh /etc/cont-init.d/03-nimbox-sre-state
COPY --chown=hermes:hermes docker/start-gateway.sh /opt/hermes/docker/start-gateway.sh
RUN chmod 755 /etc/cont-init.d/03-nimbox-sre-state /opt/hermes/docker/start-gateway.sh

# Keep Hermes running in headless/server mode
CMD ["gateway"]
