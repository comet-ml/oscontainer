import math
import multiprocessing
import os
from logging import Logger
from typing import Any

from oscontainer import NO_LIMIT
from oscontainer.constants import PER_CPU_SHARES
from oscontainer.utils import load, load_multiline_scan, load_scan


class CgroupInfo(object):
    """
    Utility class for storing info retrieved from /proc/cgroups, /proc/self/cgroup and /proc/self/mountinfo
    """

    def __init__(self, name, hierarchy_id, enabled, v1_data_complete=False,
                 cgroup_path=None, root_mount_path=None, mount_path=None):
        """
        :param name:
        :param hierarchy_id:
        :param enabled:
        :param v1_data_complete: indicating cgroup v1 data is complete for this controller
        :param cgroup_path: cgroup controller path from /proc/self/cgroup
        :param root_mount_path: root mount path from /proc/self/mountinfo. Unused for cgroup v2
        :param mount_path: mount path from /proc/self/mountinfo.
        """
        self.name = name
        self.hierarchy_id = hierarchy_id
        self.enabled = enabled
        self.v1_data_complete = v1_data_complete
        self.cgroup_path = cgroup_path
        self.root_mount_path = root_mount_path
        self.mount_path = mount_path


class CgroupController(object):
    """
   The base class for cgroup controllers
   """

    def __init__(self):
        self.subsystem_path = None

    def get_subsystem_path(self):
        return self.subsystem_path

    def read_container_param(self, param_path):
        # type: (str) -> str
        return load(path=os.path.join(self.subsystem_path, param_path))

    def read_container_params_with_format(self, param_path, scan_format):
        # type: (str, str) -> Any
        return load_scan(path=os.path.join(self.subsystem_path, param_path), scan_format=scan_format)

    def read_container_params_from_multiline(self, param_path, scan_format, match_line):
        # type: (str, str, str) -> Any
        return load_multiline_scan(path=os.path.join(self.subsystem_path, param_path),
                                   scan_format=scan_format,
                                   match_line=match_line)


class CgroupSubsystem(object):
    """
    The base class cgroup subsystems implementations (v1, v2)
    """

    def cpu_quota(self):
        # type: () -> int
        """
        Return the number of microseconds per period process is guaranteed to run.
        :return: quota time in microseconds or -1 for no quota
        """
        pass

    def cpu_period(self):
        # type: () -> int
        """
        Returns the length period in microseconds allotted for container.
        :return: period length in microseconds or -1 if not throttled.
        """
        pass

    def cpu_shares(self):
        # type: () -> int
        """
        Return the amount of cpu shares available to the process
        :return: Share number or -1 for no share setup.  (typically a number relative to 1024,  i.e., 2048
        expresses 2 CPUs worth of processing)
        """
        pass

    def cpu_cpuset_cpus(self):
        # type: () -> str
        pass

    def memory_limit_in_bytes(self):
        # type: () -> int
        """
        Return the limit of available memory for this process.
        :return: memory limit in bytes or -1 for unlimited.
        """
        pass

    def memory_usage_in_bytes(self):
        # type: () -> int
        """
        Return the amount of used memory used by this cgroup and descendants
        :return: memory usage in bytes or -1 for unlimited
        """
        pass

    def container_type(self):
        # type: () -> str
        """
        Returns cgroup container type detected (V1 or V2)
        :return: the cgroup container type detected
        """
        pass

    def active_processor_count(self, prefer_container_quota=False, host_cpu_count=None, logger=None):
        # type: (bool, int, Logger) -> int
        """
        Calculate an appropriate number of active processors to use based on these three inputs:
        * cpu affinity
        * cgroup cpu quota & cpu period
        * cgroup cpu shares

        Algorithm:

        Determine the number of available CPUs from sched_getaffinity

        If user specified a quota (quota != -1), calculate the number of
        required CPUs by dividing quota by period.

        If shares are in effect (shares != -1), calculate the number
        of CPUs required for the shares by dividing the share value
        by PER_CPU_SHARES.

        All results of division are rounded up to the next whole number.

        If neither shares or quotas have been specified, return the
        number of active processors in the system.

        If both shares and quotas have been specified, the results are
        based on the flag prefer_container_quota.

        If shares and/or quotas have been specified, the resulting number
        returned will never exceed the number of active processors.

        :param prefer_container_quota: If True, return the quota value.
        If False return the smallest value between shares or quotas.
        :param host_cpu_count: the number of host CPUs
        :param logger: the logger to use
        :return: the allotted number of CPUs
        """
        if host_cpu_count is None:
            try:
                cpu_count = len(os.sched_getaffinity(0))
            except AttributeError:
                cpu_count = multiprocessing.cpu_count()
        else:
            cpu_count = host_cpu_count
        limit_count = cpu_count
        quota_count, share_count = 0, 0

        quota = self.cpu_quota()
        period = self.cpu_period()
        share = self.cpu_shares()

        if quota > NO_LIMIT and period > 0:
            quota_count = math.ceil(float(quota) / float(period))
            if logger is not None:
                logger.debug("CPU Quota count based on quota/period: %d", quota_count)

        if share > NO_LIMIT:
            share_count = math.ceil(float(share) / float(PER_CPU_SHARES))
            if logger is not None:
                logger.debug("CPU Share count based on shares: %d", share_count)

        # If both shares and quotas are defined results depend on flag prefer_container_quota.
        # If true, limit CPU count to quota, otherwise, use minimum of shares and quotas
        if quota_count != 0 and share_count != 0:
            if prefer_container_quota:
                limit_count = quota_count
            else:
                limit_count = min(quota_count, share_count)
        elif quota_count != 0:
            limit_count = quota_count
        elif share_count != 0:
            limit_count = share_count

        if logger is not None:
            logger.debug("quota_count : share_count = %d : %d", quota_count, share_count)
            logger.debug("cpu_count : limit_count = %d : %d", cpu_count, limit_count)

        result = min(cpu_count, limit_count)
        if logger is not None:
            logger.debug("Active processors count: %d", result)

        return result
