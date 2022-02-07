import os
from typing import Optional

from oscontainer.cgroup_subsystem import CgroupController, CgroupSubsystem
from oscontainer.constants import PER_CPU_SHARES, NO_LIMIT, CGROUP_TYPE_V1
from oscontainer.errors import OSContainerError

CPU_CFS_QUOTA_US = "cpu.cfs_quota_us"
CPU_CFS_PERIOD_US = "cpu.cfs_period_us"
CPU_SHARES = "cpu.shares"
CPU_CPUSET_CPUS = "cpuset.cpus"

MEMORY_USAGE_IN_BYTES = "memory.usage_in_bytes"
MEMORY_LIMIT_IN_BYTES = "memory.limit_in_bytes"
MEMORY_USE_HIERARCHY = "memory.use_hierarchy"
MEMORY_STAT = "memory.stat"


class CgroupV1Controller(CgroupController):

    def __init__(self, root, mount_point, cgroup_path):
        # type: (str, str, str) -> None
        """
        Creates new cgroup V1 controller.
        :param root: the filesystem root for the mount_point
        :param mount_point: the mount point of the cgroup controller
        :param cgroup_path: cgroup controller path from /proc/self/cgroup
        """
        super().__init__()
        self.root = root
        self.mount_point = mount_point
        self.set_subsystem_path(cgroup_path)

    def set_subsystem_path(self, cgroup_path):
        # type: (str) -> None
        """
        Set directory to subsystem specific files based on the contents of the mountinfo and cgroup files.
        :param cgroup_path: cgroup controller path from /proc/self/cgroup
        """
        if self.root is None or cgroup_path is None:
            raise OSContainerError("either root or cgroup_path is None")

        if self.root == "/":
            # host
            self.subsystem_path = self.mount_point
            if cgroup_path != "/":
                self.subsystem_path = self.subsystem_path + cgroup_path
        else:
            # container
            if cgroup_path.startswith(self.root) and cgroup_path != self.root:
                path = cgroup_path.replace(self.root, "")
                self.subsystem_path = self.mount_point + path
            else:
                self.subsystem_path = self.mount_point


class CgroupV1MemoryController(CgroupV1Controller):
    """
    The memory controller.
    Some container runtimes set limits via cgroup hierarchy.
    If uses_mem_hierarchy set to True consider also 'memory.stat' file if everything else seems unlimited.
    """

    def __init__(self, root, mount_point, cgroup_path):
        # type: (str, str, str) -> None
        super().__init__(root, mount_point, cgroup_path)
        self.is_hierarchical = False

    def uses_mem_hierarchy(self):
        # type: () -> bool
        """
        Return whether hierarchical cgroup accounting is being setup detected.
        :return: True if hierarchical cgroup accounting is being setup detected
        """
        try:
            return int(self.read_container_param(MEMORY_USE_HIERARCHY)) > 0
        except:
            return False

    def set_subsystem_path(self, cgroup_path):
        # type: (str) -> None
        super(CgroupV1MemoryController, self).set_subsystem_path(cgroup_path)
        self.is_hierarchical = self.uses_mem_hierarchy()


class CgroupV1Subsystem(CgroupSubsystem):
    """
    The implementation of cgroup V1 subsystem
    """

    def __init__(self, cpuset, cpu, cpuacct, memory, pids=None):
        # type: (CgroupV1Controller, CgroupV1Controller, CgroupV1Controller, CgroupV1MemoryController, Optional[CgroupV1Controller]) -> None
        """
        Creates new instance with specified controllers
        :param cpuset: the cgroup controller for cpuset parameters
        :param cpu: the cgroup controller for cpu parameters
        :param cpuacct: the cgroup controller for cpuacct parameters
        :param memory: the cgroup controller for memory parameters
        :param pids: the optional cgroup controller for pids parameters
        """
        self.cpuset = cpuset
        self.cpu = cpu
        self.cpuacct = cpuacct
        self.memory = memory
        self.pids = pids

    def cpu_shares(self):
        # type: () -> int
        shares = int(self.cpu.read_container_param(CPU_SHARES))
        if shares == PER_CPU_SHARES:
            return NO_LIMIT
        return shares

    def cpu_quota(self):
        # type: () -> int
        return int(self.cpu.read_container_param(CPU_CFS_QUOTA_US))

    def cpu_period(self):
        # type: () -> int
        return int(self.cpu.read_container_param(CPU_CFS_PERIOD_US))

    def cpu_cpuset_cpus(self):
        # type: () -> str
        return self.cpuset.read_container_param(CPU_CPUSET_CPUS)

    def memory_usage_in_bytes(self):
        # type: () -> int
        return int(self.memory.read_container_param(MEMORY_USAGE_IN_BYTES))

    def memory_limit_in_bytes(self):
        # type: () -> int
        _unlimited_memory = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
        memlimit = int(self.memory.read_container_param(MEMORY_LIMIT_IN_BYTES))
        if memlimit >= _unlimited_memory:
            if self.memory.is_hierarchical:
                hier_memlimit_str = self.memory.read_container_params_from_multiline(
                    param_path=MEMORY_STAT, match_line="hierarchical_memory_limit", scan_format="%s %d")
                if len(hier_memlimit_str) == 2:
                    hier_memlimit = hier_memlimit_str[1]
                    if hier_memlimit < _unlimited_memory:
                        return hier_memlimit

            return NO_LIMIT
        else:
            return memlimit

    def container_type(self):
        # type: () -> str
        return CGROUP_TYPE_V1
