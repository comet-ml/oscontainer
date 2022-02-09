import logging
import multiprocessing
import os
from typing import Optional

from oscontainer.cgroups import build_cgroup_subsystem
from oscontainer.errors import OSContainerError

LOGGER = logging.getLogger(__name__)


class OSContainer(object):
    """
    Allows accessing parameters of the Linux container.
    """

    def __init__(self):
        self._containerized = False
        try:
            self.cgroup_subsystem = build_cgroup_subsystem()
        except Exception:
            LOGGER.warning("Failed to detect CGROUP subsystem, container not detected.")
            LOGGER.debug("CGROUP container detection failed", exc_info=True)
            return

        self.memory_limit = self.cgroup_subsystem.memory_limit_in_bytes()
        LOGGER.info("Memory Limit is: %d", self.memory_limit)

        self._containerized = True

    def active_processor_count(self, prefer_container_quota=False):
        # type: (bool) -> int
        """
        Returns the number of active processors allotted for container.
        :param prefer_container_quota: If True, return the quota value. If False return the smallest value
        between shares or quotas.
        :return: the allotted number of CPUs
        """
        self._validate_containerized()
        return self.cgroup_subsystem.active_processor_count(prefer_container_quota=prefer_container_quota)

    def container_type(self):
        # type: () -> str
        """
        Returns cgroup container type detected (V1 or V2)
        :return: the cgroup container type detected
        """
        self._validate_containerized()
        return self.cgroup_subsystem.container_type()

    def cpu_quota(self):
        # type: () -> int
        """
        Return the number of microseconds per period process is guaranteed to run.
        :return: quota time in microseconds or -1 for no quota
        """
        self._validate_containerized()
        return self.cgroup_subsystem.cpu_quota()

    def cpu_period(self):
        # type: () -> int
        """
        Returns the length period in microseconds allotted for container.
        :return: period length in microseconds or -1 if not throttled.
        """
        self._validate_containerized()
        return self.cgroup_subsystem.cpu_period()

    def cpu_shares(self):
        # type: () -> int
        """
        Return the amount of cpu shares available to the process
        :return: Share number or -1 for no share setup.  (typically a number relative to 1024,  i.e., 2048
        expresses 2 CPUs worth of processing)
        """
        self._validate_containerized()
        return self.cgroup_subsystem.cpu_shares()

    def cpu_cpuset_cpus(self):
        # type: () -> Optional[str]
        """
        Returns list of the physical numbers of the CPUs on which processes in that cpuset are allowed to execute.
        :return: the list of the physical numbers of the CPUs on which processes in that cpuset are allowed to execute.
        """
        self._validate_containerized()
        try:
            return self.cgroup_subsystem.cpu_cpuset_cpus()
        except:
            LOGGER.error("Failed to read CPUSET", exc_info=True)

        return None

    def memory_usage_in_bytes(self):
        # type: () -> int
        """
        Return the amount of used memory used by this cgroup and descendants
        :return: memory usage in bytes or -1 for unlimited
        """
        self._validate_containerized()
        return self.cgroup_subsystem.memory_usage_in_bytes()

    def memory_limit_in_bytes(self):
        # type: () -> int
        """
        Return the limit of available memory for this process.
        :return: memory limit in bytes or -1 for unlimited.
        """
        self._validate_containerized()
        return self.memory_limit

    def is_containerized(self):
        # type: () -> bool
        """
        Allows checking if container was detected.
        :return: True if CGROUP container was detected.
        """
        return self._containerized

    def print(self):
        """
        Prints collected stats about container
        """
        print("OSContainer:")
        print("==========================")
        if self._containerized:
            print("   active processors: %d" % self.active_processor_count())
            print("      container type: %s" % self.container_type())
            print("--------------------------")
            print(" > MEMORY:")
            print("--------------------------")
            print("memory limit (bytes): %d" % self.memory_limit_in_bytes())
            print("memory usage (bytes): %d" % self.memory_usage_in_bytes())
            print("--------------------------")
            print(" > CPU:")
            print("--------------------------")
            print("               quota: %d" % self.cpu_quota())
            print("              period: %d" % self.cpu_period())
            print("              shares: %d" % self.cpu_shares())
            print("         cpuset cpus: %s" % self.cpu_cpuset_cpus())
            print("==========================")
        else:
            print("No container found")
            print("==========================")

        # print host system info
        print("System information:")
        print("==========================")
        print("multiprocessing.cpu_count: %r" % multiprocessing.cpu_count())
        try:
            cpu_affinity = os.sched_getaffinity(0)
            print("     process cpu affinity: %r" % cpu_affinity)
        except:
            print("Failed to read CPU affinity")
        print("==========================")

    def _validate_containerized(self):
        if not self._containerized:
            raise OSContainerError("cgroup subsystem not available")
