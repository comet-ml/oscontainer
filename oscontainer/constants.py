
# The value to indicate NO LIMIT parameter
NO_LIMIT = -1

# PER_CPU_SHARES has been set to 1024 because CPU shares' quota
# is commonly used in cloud frameworks like Kubernetes[1],
# AWS[2] and Mesos[3] in a similar way. They spawn containers with
# --cpu-shares option values scaled by PER_CPU_SHARES.
PER_CPU_SHARES = 1024

SUBSYS_MEMORY = "memory"
SUBSYS_CPUSET = "cpuset"
SUBSYS_CPU = "cpu"
SUBSYS_CPUACCT = "cpuacct"
SUBSYS_PIDS = "pids"

CGROUP_TYPE_V2 = "cgroup2"
CGROUP_TYPE_V1 = "cgroup"
