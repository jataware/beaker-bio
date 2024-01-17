FROM python:3.10

USER root

# RUN apt add-repository ppa:ubuntugis/ppa
RUN apt-get update &&\
    apt-get install -y build-essential gcc g++ gdal-bin libgdal-dev python3-all-dev libspatialindex-dev

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

RUN pip install numpy==1.24.3 

WORKDIR /bio_context
COPY --chown=1000:1000 . /bio_context/

RUN pip install hatch

RUN useradd -m jupyter
USER jupyter
RUN pip install .
RUN pip install git+https://github.com/indralab/mira.git

WORKDIR /jupyter
COPY context.json /jupyter
CMD ["python", "-m", "beaker_kernel.server.main", "--ip", "0.0.0.0"]