import logging
from typing import Dict, List, Tuple, Union

from oscontainer.scanf import scanf

from oscontainer.cgroup_subsystem import CgroupInfo, CgroupSubsystem
from oscontainer.cgroup_v1_subsystem import CgroupV1Controller, CgroupV1MemoryController, CgroupV1Subsystem
from oscontainer.cgroup_v2_subsystem import CgroupV2Controller, CgroupV2Subsystem
from oscontainer.constants import SUBSYS_PIDS, SUBSYS_MEMORY, SUBSYS_CPU, SUBSYS_CPUACCT, \
    SUBSYS_CPUSET, CGROUP_TYPE_V2, CGROUP_TYPE_V1
from oscontainer.errors import OSContainerError

LOGGER = logging.getLogger(__name__)

# The common paths to the related cgroup files
PROC_SELF_MOUNTINFO = "/proc/self/mountinfo"
PROC_SELF_CGROUP = "/proc/self/cgroup"
PROC_CGROUPS = "/proc/cgroups"


def build_cgroup_subsystem(proc_self_cgroup=PROC_SELF_CGROUP,
                           proc_self_mountinfo=PROC_SELF_MOUNTINFO,
                           proc_cgroups=PROC_CGROUPS):
    # type: (str,str,str) -> CgroupSubsystem
    """
    Builds appropriate cgroup subsystem.
    :param proc_cgroups: the optional path to the '/proc/cgroups' file.
    :param proc_self_cgroup: the optional path to the '/proc/self/cgroup' file.
    :param proc_self_mountinfo: the optional path to the '/proc/self/mountinfo' file.
    :return: the cgroup subsystem
    """
    subsystem_info = determine_type(proc_self_cgroup=proc_self_cgroup,
                                    proc_self_mountinfo=proc_self_mountinfo,
                                    proc_cgroups=proc_cgroups)
    if subsystem_info is None:
        raise OSContainerError("Required subsystem files not found")

    cgroup_type, cg_infos = subsystem_info
    if cgroup_type == CGROUP_TYPE_V2:
        info = cg_infos[SUBSYS_MEMORY]
        controller = CgroupV2Controller(info.mount_path, info.cgroup_path)
        return CgroupV2Subsystem(controller)

    # Cgroup v1 case:
    # Use info gathered previously from /proc/self/cgroup and map host mount point to
    # local one via /proc/self/mountinfo content above
    #
    # Docker example:
    # 5:memory:/docker/6558aed8fc662b194323ceab5b964f69cf36b3e8af877a14b80256e93aecb044
    #
    # Host example:
    # 5:memory:/user.slice
    #
    # Construct a path to the process specific memory and cpuset cgroup directory.
    #
    # For a container running under Docker from memory example above the paths would be:
    #
    # /sys/fs/cgroup/memory
    #
    # For a Host from memory example above the path would be:
    #
    # /sys/fs/cgroup/memory/user.slice
    assert cgroup_type == CGROUP_TYPE_V1, "cgroup v1 expected"
    cpuset, cpu, cpuacct, memory, pids = None, None, None, None, None
    for name, info in cg_infos.items():
        if info.v1_data_complete:
            if name == SUBSYS_MEMORY:
                memory = CgroupV1MemoryController(root=info.root_mount_path, mount_point=info.mount_path,
                                                  cgroup_path=info.cgroup_path)
            elif name == SUBSYS_CPUSET:
                cpuset = CgroupV1Controller(root=info.root_mount_path, mount_point=info.mount_path,
                                            cgroup_path=info.cgroup_path)
            elif name == SUBSYS_CPU:
                cpu = CgroupV1Controller(root=info.root_mount_path, mount_point=info.mount_path,
                                         cgroup_path=info.cgroup_path)
            elif name == SUBSYS_CPUACCT:
                cpuacct = CgroupV1Controller(root=info.root_mount_path, mount_point=info.mount_path,
                                             cgroup_path=info.cgroup_path)
            elif name == SUBSYS_PIDS:
                pids = CgroupV1Controller(root=info.root_mount_path, mount_point=info.mount_path,
                                          cgroup_path=info.cgroup_path)
        else:
            LOGGER.info("CgroupInfo for %s not complete", name)

    return CgroupV1Subsystem(cpuset=cpuset, cpu=cpu, cpuacct=cpuacct, memory=memory, pids=pids)


def determine_type(proc_cgroups, proc_self_cgroup, proc_self_mountinfo):
    # type: (str, str, str) -> Union[None, Tuple[str, Dict[str, CgroupInfo]]]
    """
    Determines the type of the cgroups filesystem. Returns the type detected or None if failed.

    :param proc_cgroups: the path to the '/proc/cgroups' file.
    :param proc_self_cgroup: the path to the '/proc/self/cgroup' file.
    :param proc_self_mountinfo: the path to the '/proc/self/mountinfo' file.
    :return: the Tuple with cgroup filesystem type and dictionary of populated CgroupInfo
    """

    # Read /proc/cgroups to be able to distinguish cgroups v2 vs cgroups v1.
    subsys_controllers = [SUBSYS_PIDS, SUBSYS_MEMORY, SUBSYS_CPU, SUBSYS_CPUACCT, SUBSYS_CPUSET]
    cg_infos = _read_cgroup_infos(proc_cgroups=proc_cgroups,
                                  subsys_controllers=subsys_controllers)  # type: Dict[str, CgroupInfo]

    # True for cgroups v2 (unified hierarchy)
    is_cgroupsV2 = True
    # True if all required controllers, memory, cpu, cpuset, cpuacct are enabled
    all_required_controllers_enabled = True
    for k, v in cg_infos.items():
        # pids controller is optional. All other controllers are required
        if k != SUBSYS_PIDS:
            is_cgroupsV2 = is_cgroupsV2 and v.hierarchy_id == 0
            all_required_controllers_enabled = all_required_controllers_enabled and v.enabled

    if not all_required_controllers_enabled:
        # one or more of required controllers disabled, disable container support
        LOGGER.info("One or more required CGROUP controllers disabled at kernel level.")
        return None

    # Read /proc/self/cgroup into cg_infos
    _read_proc_self_cgroup(cg_infos=cg_infos, proc_self_cgroup=proc_self_cgroup, is_cgroups_v2=is_cgroupsV2)

    # Read /proc/self/mountinfo and find mount points
    cgroupv2_mount_point_found, any_cgroup_mounts_found = _read_mount_points(
        proc_self_mountinfo=proc_self_mountinfo, cg_infos=cg_infos,
        is_cgroups_v2=is_cgroupsV2, subsys_controllers=subsys_controllers)

    # Neither cgroup2 nor cgroup filesystems mounted via /proc/self/mountinfo
    # No point in continuing.
    if not any_cgroup_mounts_found:
        LOGGER.warning("No relevant cgroup controllers mounted.")
        return None

    if is_cgroupsV2:
        if not cgroupv2_mount_point_found:
            LOGGER.warning("Mount point for cgroupv2 not found in /proc/self/mountinfo")
            return None
        return CGROUP_TYPE_V2, cg_infos

    # The rest is cgroups v1
    LOGGER.debug("Detected cgroups hybrid or legacy hierarchy, using cgroups v1 controllers")
    for k in cg_infos:
        if not cg_infos[k].v1_data_complete and k != SUBSYS_PIDS:
            LOGGER.warning("Required cgroup v1 %s subsystem not found" % k)
            return None

    return CGROUP_TYPE_V1, cg_infos


def _read_mount_points(proc_self_mountinfo, cg_infos, is_cgroups_v2, subsys_controllers):
    # type: (str, Dict[str, CgroupInfo], bool, List[str]) -> (bool, bool)
    """
    Finds various mount points by reading /proc/self/mountinfo file.
    mountinfo format is documented at https://www.kernel.org/doc/Documentation/filesystems/proc.txt

    :param proc_self_mountinfo: the path to the /proc/self/mountinfo file.
    :param cg_infos: the dictionary with control group controllers.
    :param is_cgroups_v2: if True it is cgroup v2 was detected before.
    :param subsys_controllers: the list with names of subsystem controllers.
    :return: (cgroupv2_mount_point_found, any_cgroup_mounts_found)
    """
    # Find various mount points by reading /proc/self/mountinfo
    # mountinfo format is documented at https://www.kernel.org/doc/Documentation/filesystems/proc.txt
    #
    # 496 495 0:30 / /sys/fs/cgroup ro,nosuid,nodev,noexec,relatime - cgroup2 cgroup rw
    cgroupv2_mount_point_found = False
    any_cgroup_mounts_found = False
    LOGGER.debug("Reading mountinfo from: %s", proc_self_mountinfo)
    with open(proc_self_mountinfo, "r") as f:
        for line in f:
            LOGGER.debug(line)
            # Cgroup v2 relevant info. We only look for the mount_path if is_cgroupsV2
            # to avoid memory stomping of the mount_path later on in the cgroup v1
            # block in the hybrid case.
            if is_cgroups_v2:
                fields = scanf("%*d %*d %*d:%*d %*s %s %*s - %s %*s %*s", line)
                if fields is not None and len(fields) == 2:
                    tmp_mount_point, tmp_fs_type = fields
                    if not cgroupv2_mount_point_found and tmp_fs_type == CGROUP_TYPE_V2:
                        cgroupv2_mount_point_found = True
                        any_cgroup_mounts_found = True
                        for k in cg_infos:
                            assert cg_infos[k].mount_path is None, "mount_path memory stomping"
                            cg_infos[k].mount_path = tmp_mount_point

            # Cgroup v1 relevant info
            # Find the cgroup mount point for memory, cpuset, cpu, cpuacct, pids
            #
            # Example for docker:
            # 219 214 0:29 /docker/7208cebd00fa5f2e342b1094f7bed87fa25661471a4637118e65f1c995be8a34 /sys/fs/cgroup/memory ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,memory
            #
            # Example for host:
            # 34 28 0:29 / /sys/fs/cgroup/memory rw,nosuid,nodev,noexec,relatime shared:16 - cgroup cgroup rw,memory
            # 44 31 0:39 / /sys/fs/cgroup/pids rw,nosuid,nodev,noexec,relatime shared:23 - cgroup cgroup rw,pids
            fields = scanf("%*d %*d %*d:%*d %s %s %*s - %s %*s %s", line)
            if fields is not None and len(fields) == 4:
                tmp_root, tmp_mount, tmp_fs_type, tmp_cgroups = fields
                if tmp_fs_type != CGROUP_TYPE_V1:
                    # Skip cgroup2 fs lines on hybrid or unified hierarchy.
                    continue

                for controller in tmp_cgroups.split(","):
                    if controller in subsys_controllers:
                        any_cgroup_mounts_found = True
                        if controller == SUBSYS_CPUSET:
                            if cg_infos[SUBSYS_CPUSET].mount_path is not None:
                                # On some systems duplicate cpuset controllers get mounted in addition to
                                # the main cgroup controllers most likely under /sys/fs/cgroup. In that
                                # case pick the one under /sys/fs/cgroup and discard others.
                                if cg_infos[SUBSYS_CPUSET].mount_path.find("/sys/fs/cgroup") > 0:
                                    LOGGER.warning("Duplicate cpuset controllers detected. Picking %s, skipping %s.",
                                                   tmp_mount, cg_infos[SUBSYS_CPUSET].mount_path)
                                    cg_infos[SUBSYS_CPUSET].mount_path = tmp_mount
                                else:
                                    LOGGER.warning("Duplicate cpuset controllers detected. Picking %s, skipping %s.",
                                                   cg_infos[SUBSYS_CPUSET].mount_path, tmp_mount)
                            else:
                                cg_infos[SUBSYS_CPUSET].mount_path = tmp_mount
                        else:
                            assert cg_infos[controller].mount_path is None, "stomping of mount_path of %s" % controller
                            cg_infos[controller].mount_path = tmp_mount

                        cg_infos[controller].root_mount_path = tmp_root
                        cg_infos[controller].v1_data_complete = True

    return cgroupv2_mount_point_found, any_cgroup_mounts_found


def _read_cgroup_infos(proc_cgroups, subsys_controllers):
    # type: (str, List[str]) -> Dict[str, CgroupInfo]
    """
    Read /proc/cgroups to be able to distinguish cgroups v2 vs cgroups v1.

    For cgroups v1 hierarchy (hybrid or legacy), cpu, cpuacct, cpuset, memory controllers
    must have non-zero for the hierarchy ID field and relevant controllers mounted.
    Conversely, for cgroups v2 (unified hierarchy), cpu, cpuacct, cpuset, memory
    controllers must have hierarchy ID 0 and the unified controller mounted.

    :param proc_cgroups: the path to the '/proc/cgroups' file.
    :param subsys_controllers: the list with names of subsys controllers.
    :return: the dictionary with info about controllers of control groups.
    """
    # subsys_name	hierarchy	num_cgroups	enabled
    # cpuset	        0	        36	        1
    cg_infos = dict()
    LOGGER.debug("Reading cgroups info from: %s", proc_cgroups)
    with open(proc_cgroups, "r") as f:
        for line in f:
            LOGGER.debug(line)
            res = scanf("%s %d %*d %d", line)
            if res is None or len(res) != 3:
                continue

            name, hierarchy_id, enabled = res
            if name in subsys_controllers:
                cg_infos[name] = CgroupInfo(name, hierarchy_id, bool(enabled))

    return cg_infos


def _read_proc_self_cgroup(proc_self_cgroup, cg_infos, is_cgroups_v2):
    # type: (str, Dict[str, CgroupInfo], bool) -> bool
    """
    Reads /proc/self/cgroup and determine:
     - the cgroup path for cgroups v2 or
     - on a cgroups v1 system, collect info for mapping
       the host mount point to the local one via /proc/self/mountinfo below.

    :param cg_infos: the dictionary with control group controllers.
    :param proc_self_cgroup: the file path to the '/proc/self/cgroup' file.
    :param is_cgroups_v2: if True it is cgroup v2 was detected before.
    :return: True if records was found
    """
    # 0::/ (cgroups v2)
    # 8:memory:/docker/container-sha (cgroups v1)
    LOGGER.debug("Reading self cgroups info from: %s", proc_self_cgroup)
    found = False
    with open(proc_self_cgroup, "r") as f:
        for line in f:
            LOGGER.debug(line)
            vals = line.split(":")
            if len(vals) != 3:
                continue

            hierarchy_id = int(vals[0].strip())
            controllers = vals[1].strip()
            cgroup_path = vals[2].strip()
            found = True

            if is_cgroups_v2:
                for k in cg_infos:
                    cg_infos[k].cgroup_path = cgroup_path
            else:
                for controller in controllers.split(","):
                    if controller in cg_infos:
                        assert hierarchy_id == cg_infos[controller].hierarchy_id, \
                            "/proc/cgroups and /proc/self/cgroup hierarchy mismatch for %s" % controller
                        cg_infos[controller].cgroup_path = cgroup_path.strip()

    if not is_cgroups_v2:
        for cg_info in cg_infos.values():
            if cg_info.cgroup_path is None:
                found = False

    return found
