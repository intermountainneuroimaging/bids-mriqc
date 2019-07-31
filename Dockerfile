# Use the latest Python 3 docker image
FROM poldracklab/mriqc:latest

MAINTAINER Flywheel <support@flywheel.io>

# Configure environment
#ENV PATH="/usr/local/miniconda/bin:$PATH"

# Save docker environ
RUN python -c 'import os, json; f = open("/tmp/gear_environ.json", "w"); json.dump(dict(os.environ), f)' 
RUN pip install flywheel-sdk
RUN pip install flywheel-bids
#############################################

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}

# Copy executable/manifest to Gear
COPY run ${FLYWHEEL}/run
COPY manifest.json ${FLYWHEEL}/manifest.json

# Configure entrypoint
RUN chmod a+x /flywheel/v0/run
ENTRYPOINT ["/flywheel/v0/run"]
#ENTRYPOINT ["/bin/bash"]
