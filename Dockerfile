# The template BIDS app repo is used for the testing example here.
## 23.1.0 runs python 3.12
FROM nipreps/mriqc:22.0.6
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
    tree \
    python3-pip \
    linux-libc-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN python -m venv /opt/flypy
ENV PATH="/opt/flypy/bin:$PATH"

# Installing main dependencies
COPY requirements.txt $FLYWHEEL/

# Verified with `which pip` that pip is /opt/flypy/bin/pip
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r $FLYWHEEL/requirements.txt

# Installing the current project (most likely to change, above layer can be cached)
COPY ./ $FLYWHEEL/
RUN mv $FLYWHEEL/templateflow /templateflow && \
    chmod -R 777 /templateflow
RUN pip install --no-cache-dir .

## add standalone install of templateflow from local download
# Installing the current project (most likely to change, above layer can be cached)
ENV TEMPLATEFLOW_HOME="/templateflow"

### Install reprozip
#RUN apt-get update && \
#   apt-get install -y --no-install-recommends  \
#   libsqlite3-dev \
#   libssl-dev \
#   libffi-dev \
#   reprozip && \
#   apt-get clean && \
#   rm -rf /var/lib/apt/lists/*
##
### Turn off messaging about anonymous statistic reporting
#RUN reprozip usage_report --disable
#
## Configure entrypoint
RUN chmod a+x $FLYWHEEL/run.py
ENTRYPOINT ["/opt/flypy/bin/python", "/flywheel/v0/run.py"]
