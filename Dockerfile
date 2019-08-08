# Use the latest Python 3 docker image
FROM poldracklab/mriqc:0.15.1

MAINTAINER Flywheel <support@flywheel.io>

# Save docker environ
RUN python -c 'import os, json; f = open("/tmp/gear_environ.json", "w"); json.dump(dict(os.environ), f)' 

RUN apt-get update && apt-get install -y zip

RUN pip install --pre flywheel-sdk
RUN pip install flywheel-bids
RUN pip install psutil

RUN npm install -g bids-validator

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}

# Copy executable/manifest to Gear
COPY run ${FLYWHEEL}/run
COPY manifest.json ${FLYWHEEL}/manifest.json

COPY mriqc.html.zip ${FLYWHEEL}/mriqc.html.zip

# Configure entrypoint
RUN chmod a+x /flywheel/v0/run
ENTRYPOINT ["/flywheel/v0/run"]
