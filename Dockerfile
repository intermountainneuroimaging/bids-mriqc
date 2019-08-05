# Use the latest Python 3 docker image
FROM poldracklab/mriqc:0.15.1

MAINTAINER Flywheel <support@flywheel.io>

# Save docker environ
RUN python -c 'import os, json; f = open("/tmp/gear_environ.json", "w"); json.dump(dict(os.environ), f)' 

RUN pip install flywheel-sdk
RUN pip install flywheel-bids

RUN npm install -g bids-validator

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}

# Copy executable/manifest to Gear
COPY run ${FLYWHEEL}/run
COPY manifest.json ${FLYWHEEL}/manifest.json

# Configure entrypoint
RUN chmod a+x /flywheel/v0/run
ENTRYPOINT ["/flywheel/v0/run"]
