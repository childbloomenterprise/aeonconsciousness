# Browser/runtime versions match; dependency list deliberately excludes NAT/world.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
WORKDIR /opt/aeon
COPY . /opt/aeon
RUN python -m pip install --no-cache-dir -c deployment/requirements.txt ".[deployment]" \
    && mkdir -p /data/tasks /work \
    && chown -R pwuser:pwuser /data /work
ENV PYTHONUNBUFFERED=1 AEON_CHROMIUM_SANDBOX=1
USER pwuser
WORKDIR /work
ENTRYPOINT ["aeon", "--task-root", "/data/tasks"]
CMD ["doctor"]
