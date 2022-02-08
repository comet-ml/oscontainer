import math

from oscontainer.constants import CGROUP_TYPE_V2, PER_CPU_SHARES, NO_LIMIT
from oscontainer.cgroup_subsystem import CgroupController, CgroupSubsystem
from oscontainer.utils import limit_from_str

CPU_WEIGHT = "cpu.weight"
CPU_MAX = "cpu.max"
CPU_CPUSET_CPUS = "cpuset.cpus"
CPU_CPUSET_CPUS_EFFECTIVE = "cpuset.cpus.effective"
MEMORY_CURRENT = "memory.current"
MEMORY_MAX = "memory.max"


class CgroupV2Controller(CgroupController):

    def __init__(self, mount_path, cgroup_path):
        # type: (str, str) -> None
        """
        Creates new cgroup V2 controller.
        :param mount_path: the mount path of the cgroup v2 hierarchy
        :param cgroup_path: the cgroup path for the controller
        """
        super().__init__()
        self.mount_path = mount_path
        self.cgroup_path = cgroup_path
        self.subsystem_path = self._create_subsystem_path(mount_path, cgroup_path)

    @staticmethod
    def _create_subsystem_path(mount_path, cgroup_path):
        # type: (str, str) -> str
        return mount_path + cgroup_path


class CgroupV2Subsystem(CgroupSubsystem):
    """
    The implementation for cgroup V2
    """

    def __init__(self, unified):
        # type: (CgroupV2Controller) -> None
        """
        Creates new instance.
        :param unified: the unified cgroup controller
        """
        self.unified = unified

    def cpu_shares(self):
        # type: () -> int
        shares = int(self.unified.read_container_param(CPU_WEIGHT))
        if shares == 100:
            # Convert default value of 100 to no shares setup
            return NO_LIMIT

        # CPU shares (OCI) value needs to get translated into
        # a proper Cgroups v2 value. See:
        # https://github.com/containers/crun/blob/master/crun.1.md#cpu-controller
        #
        # Use the inverse of (x == OCI value, y == cgroupsv2 value):
        # ((262142 * y - 1)/9999) + 2 = x
        x = 262142 * shares - 1
        frac = float(x) / 9999.0
        x = int(frac) + 2
        if x <= PER_CPU_SHARES:
            # will always map to 1 CPU
            return x

        # Since the scaled value is not precise, return the closest
        # multiple of PER_CPU_SHARES for a more conservative mapping
        f = x / PER_CPU_SHARES
        lower_multiple = math.floor(f) * PER_CPU_SHARES
        upper_multiple = math.ceil(f) * PER_CPU_SHARES
        distance_lower = max(lower_multiple, x) - min(lower_multiple, x)
        distance_upper = max(upper_multiple, x) - min(upper_multiple, x)
        if distance_lower <= distance_upper:
            return lower_multiple
        else:
            return upper_multiple

    def cpu_quota(self):
        # type: () -> int
        cpu_quota_res = self.unified.read_container_params_with_format(CPU_MAX, scan_format="%s %*d")
        if len(cpu_quota_res) == 0:
            return NO_LIMIT
        return limit_from_str(cpu_quota_res[0])

    def cpu_period(self):
        # type: () -> int
        cpu_period_res = self.unified.read_container_params_with_format(CPU_MAX, scan_format="%*s %d")
        if len(cpu_period_res) == 0:
            return NO_LIMIT
        return cpu_period_res[0]

    def cpu_cpuset_cpus(self):
        # type: () -> str
        cpuset = self.unified.read_container_param(CPU_CPUSET_CPUS)
        if cpuset is None or cpuset == "":
            cpuset = self.unified.read_container_param(CPU_CPUSET_CPUS_EFFECTIVE)
        return cpuset

    def memory_usage_in_bytes(self):
        # type: () -> int
        return int(self.unified.read_container_param(MEMORY_CURRENT))

    def memory_limit_in_bytes(self):
        # type: () -> int
        memory_str = self.unified.read_container_param(MEMORY_MAX)
        return limit_from_str(memory_str)

    def container_type(self):
        # type: () -> str
        return CGROUP_TYPE_V2
