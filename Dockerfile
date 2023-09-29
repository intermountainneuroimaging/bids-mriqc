FROM python:3.9-slim as fw_base
ENV FLYWHEEL="/flywheel/v0"
WORKDIR ${FLYWHEEL}

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

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

# Install reprozip
RUN apt-get update && \
    apt-get install -y --no-install-recommends  \
    libsqlite3-dev \
    libssl-dev \
    libffi-dev \
    reprozip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Turn off messaging about anonymous statistic reporting
RUN reprozip usage_report --disable

# Installing main dependencies
COPY requirements.txt $FLYWHEEL/
RUN pip install --no-cache-dir -r $FLYWHEEL/requirements.txt

COPY . $FLYWHEEL/
RUN pip install --no-cache-dir .
#
#
## Configure entrypoint
#RUN chmod a+x $FLYWHEEL/run.py
#ENTRYPOINT ["reprozip", "trace", "--dont-find-inputs-outputs", "python","/flywheel/v0/run.py"]

# Isolate the versions of the dependencies within the BIDS App
# from the (potentially updated) Flywheel dependencies by copying
# the venv with the pip installed Flyhweel deps.

## The template BIDS app repo is used for the testing example here.
#### REPLACE WITH THE BIDS APP OFFICIAL IMAGE
#FROM bids/example as bids_runner
#ENV FLYWHEEL="/flywheel/v0"
#WORKDIR ${FLYWHEEL}
#
## Install build dependencies
#RUN apt-get update && \
#    apt-get install -y  \
#    curl \
#    build-essential \
#    libssl-dev \
#    zlib1g-dev \
#    libncurses5-dev \
#    libncursesw5-dev \
#    libreadline-dev \
#    libsqlite3-dev \
#    libgdbm-dev \
#    libdb5.3-dev \
#    libbz2-dev \
#    libexpat1-dev \
#    liblzma-dev \
#    libffi-dev \
#    uuid-dev \
#    && \
#    apt-get clean
#
## Download Python 3.9 source code
#RUN cd /tmp && \
#    curl -O https://www.python.org/ftp/python/3.9.12/Python-3.9.12.tgz && \
#    tar xzf Python-3.9.12.tgz
#
## Build and install Python 3.9
#RUN cd /tmp/Python-3.9.12 && \
#    ./configure && \
#    make && \
#    make altinstall
#
#COPY --from=fw_base /opt/venv /opt/venv/flypy
## Update the softlink to point to Python 3.9 in bids_runner
##RUN ln -sf /usr/local/bin/python3.9 /opt/venv/flypy/bin/python
#ENV PATH="/opt/venv/flypy/bin:$PATH"
#
## Installing the current project (most likely to change, above layer can be cached)
#COPY ./ $FLYWHEEL/
#
## Configure entrypoint
#RUN chmod a+x $FLYWHEEL/run.py
#ENTRYPOINT ["/bin/bash", "-c", "source /opt/venv/flypy/bin/activate && python3.9 /flywheel/v0/run.py"]