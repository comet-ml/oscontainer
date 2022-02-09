[![Python package](https://github.com/yaricom/oscontainer/actions/workflows/python-package.yml/badge.svg)](https://github.com/yaricom/oscontainer/actions/workflows/python-package.yml)
[![pypi](https://img.shields.io/pypi/v/oscontainer.svg)](https://pypi.org/project/oscontainer/)
![versions](https://img.shields.io/pypi/pyversions/oscontainer.svg)
[![license](https://img.shields.io/github/license/yaricom/oscontainer.svg)](https://github.com/yaricom/oscontainer/blob/master/LICENSE)

# Overview

The simple library to gather CPU and memory resource limits from within OS Container bases on Linux.

## Install

```bash
pip install oscontainer
```

## Usage in code

The library can be used to acquire current limits exposed to the container or process as following:

```python
from oscontainer import OSContainer

# Get the container instance
container = OSContainer()

# Check if current process runs inside container
if container.is_containerized():
    # Get active processors
    cpus_count = container.active_processor_count()
    
    # Get the limit of available memory for this process.
    mem_limit = container.memory_limit_in_bytes()
else:
    print("No Container support detected")
```

For extra metrics available see [OSContainer](./oscontainer/os_container.py).

## Run in Docker from source code

To run library in the test container you need to build the docker image and run it as container.

Checkout the repository.

```bash
git clone git@github.com:yaricom/oscontainer.git
```

Build local image with `oscontainer` name.

```bash
cd oscontainer

docker build -f Dockerfile -t oscontainer . 
```

Run the image we built within container with specific CPU limits set. 
For details about setting container resources limits with Docker, see: [Runtime options with Memory, CPUs, and GPUs](https://docs.docker.com/config/containers/resource_constraints).

The following command will start container and open interactive shell:

```bash
docker run -it --cpus=".5" oscontainer /bin/bash
```

Now, execute `main.py` script within shell to see resource constraints that was detected:

```bash
python main.py 
```

This will produce the output like following:

```text
OSContainer:
==========================
   active processors: 1
      container type: cgroup2
--------------------------
 > MEMORY:
--------------------------
memory limit (bytes): -1
memory usage (bytes): 8413184
--------------------------
 > CPU:
--------------------------
               quota: 50000
              period: 100000
              shares: -1
         cpuset cpus: 0-2
==========================
System information:
==========================
multiprocessing.cpu_count: 3
     process cpu affinity: {0, 1, 2}
==========================
```