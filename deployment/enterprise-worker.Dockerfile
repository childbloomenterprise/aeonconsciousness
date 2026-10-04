FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
WORKDIR /opt/aeon
COPY . /opt/aeon
RUN python -m pip install --no-cache-dir -c deployment/requirements.txt ".[deployment]"
ENV PYTHONUNBUFFERED=1
USER pwuser
WORKDIR /job
CMD ["python", "-m", "aeon_enterprise.execute", "--job-root", "/job"]
