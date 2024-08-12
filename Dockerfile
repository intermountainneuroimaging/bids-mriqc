# Keep the python at 3.9-slim to integrate well with
# the mriqc image.
FROM python:3.9-slim as fw_base
ENV FLYWHEEL="/flywheel/v0"
WORKDIR ${FLYWHEEL}

# Dev install. git for pip editable install.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean
RUN apt-get install --no-install-recommends -y \
   git \
   build-essential \
   zip \
   nodejs \
   tree && \
   apt-get clean && \
   rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

## Install reprozip
#RUN apt-get update && \
#    apt-get install -y --no-install-recommends  \
#    libsqlite3-dev \
#    libssl-dev \
#    libffi-dev \
#    reprozip && \
#    apt-get clean && \
#    rm -rf /var/lib/apt/lists/*
#
## Turn off messaging about anonymous statistic reporting
#RUN reprozip usage_report --disable

RUN python -m venv /opt/flypy
ENV PATH="/opt/flypy/bin:$PATH"

# Installing main dependencies
COPY requirements.txt $FLYWHEEL/

# Verified with `which pip` that pip is /opt/flypy/bin/pip
RUN pip install --no-cache-dir -U pip
RUN pip install --no-cache-dir -r $FLYWHEEL/requirements.txt

COPY ./ $FLYWHEEL/
RUN pip install --no-cache-dir .

# Isolate the versions of the dependencies within the BIDS App
# from the (potentially updated) Flywheel dependencies by copying
# the venv with the pip installed Flyhweel deps.

# The template BIDS app repo is used for the testing example here.
### 23.1.0 runs python 3.9.12
FROM nipreps/mriqc:24.0.0 as bids_runner
ENV FLYWHEEL="/flywheel/v0"
WORKDIR ${FLYWHEEL}

COPY --from=fw_base /usr/local /usr/local
COPY --from=fw_base /opt/flypy /opt/flypy
# Update the softlink to point to fw_base's version of python in bids_runner
RUN ln -sf /usr/local/bin/python3.9 /opt/flypy/bin/python

# Installing the current project (most likely to change, above layer can be cached)
COPY ./ $FLYWHEEL/
#
## Configure entrypoint
RUN chmod a+x $FLYWHEEL/run.py
ENTRYPOINT ["/opt/flypy/bin/python", "/flywheel/v0/run.py"]
