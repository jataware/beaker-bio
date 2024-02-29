FROM localhost:5000/askem-julia:mimi AS JULIA_BASE_IMAGE

FROM python:3.10

USER root

# Install custom Julia
ENV JULIA_PATH=/usr/local/julia
ENV JULIA_DEPOT_PATH=/usr/local/julia
ENV JULIA_PROJECT=/home/jupyter/.julia/environments/askem

COPY --chown=1000:1000 --from=JULIA_BASE_IMAGE /usr/local/julia /usr/local/julia
COPY --chown=1000:1000 --from=JULIA_BASE_IMAGE /Project.toml /Manifest.toml /home/jupyter/.julia/environments/askem/
RUN chmod -R 777 /usr/local/julia/logs
RUN ln -sf /usr/local/julia/bin/julia /usr/local/bin/julia

USER root

# RUN apt add-repository ppa:ubuntugis/ppa
RUN apt-get update &&\
    apt-get install -y build-essential gcc g++ gdal-bin libgdal-dev python3-all-dev libspatialindex-dev \
            graphviz libgraphviz-dev 

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

RUN pip install numpy==1.24.3 

WORKDIR /bio_context
COPY --chown=1000:1000 . /bio_context/

RUN pip install hatch

RUN useradd -m jupyter
USER jupyter
RUN pip install -e .
RUN pip install git+https://github.com/indralab/mira.git

WORKDIR /jupyter
RUN /usr/local/julia/bin/julia -e 'using IJulia; IJulia.installkernel("julia"; julia=`/usr/local/julia/bin/julia --threads=4`)'
COPY context.json /jupyter
CMD ["python", "-m", "beaker_kernel.server.main", "--ip", "0.0.0.0"]
