# Use the latest Python 3 docker image
FROM nipreps/mriqc:22.0.6

MAINTAINER Flywheel <support@flywheel.io>

# Remove expired LetsEncrypt cert
#			RUN rm /usr/share/ca-certificates/mozilla/DST_Root_CA_X3.crt && \
		    RUN update-ca-certificates
			ENV REQUESTS_CA_BUNDLE "/etc/ssl/certs/ca-certificates.crt"

RUN apt-get update && apt-get install -y zip && rm -rf /var/lib/apt/lists/*

RUN npm install -g bids-validator@1.9.9

COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/pip

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}

# Save docker environ
ENV PYTHONUNBUFFERED 1

# Create Flywheel User
RUN adduser --disabled-password --gecos "Flywheel User" flywheel
# Copy executable/manifest to Gear
COPY manifest.json ${FLYWHEEL}/manifest.json
COPY utils ${FLYWHEEL}/utils
COPY run.py ${FLYWHEEL}/run.py
RUN python -c 'import os, json; f = open("/flywheel/v0/gear_environ.json", "w"); json.dump(dict(os.environ), f)'

# Configure entrypoint
RUN chmod a+x /flywheel/v0/run.py && chown -R flywheel ${FLYWHEEL}
ENTRYPOINT ["/flywheel/v0/run.py"]

