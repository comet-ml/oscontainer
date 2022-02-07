import os

import pytest

from oscontainer.cgroup_subsystem import CgroupInfo
from oscontainer.cgroup_v1_subsystem import CgroupV1Subsystem, CgroupV1Controller, CgroupV1MemoryController
from oscontainer.cgroup_v2_subsystem import CgroupV2Subsystem, CgroupV2Controller
from oscontainer.cgroups import _read_cgroup_infos, _read_mount_points, _read_proc_self_cgroup, determine_type, \
    build_cgroup_subsystem
from oscontainer.constants import SUBSYS_PIDS, SUBSYS_MEMORY, SUBSYS_CPU, SUBSYS_CPUACCT, SUBSYS_CPUSET, \
    CGROUP_TYPE_V2, CGROUP_TYPE_V1

DATA_PATH = "./data/"
FILE_PROC_CGROUPS_V2 = DATA_PATH + "proc_cgroups_v2"
FILE_MOUNTINFO_CGROUP2 = DATA_PATH + "mountinfo_cgroup2"
FILE_SELF_CGROUPS_V2 = DATA_PATH + "self_cgroups_v2"

FILE_PROC_CGROUPS_V1 = DATA_PATH + "proc_cgroups_v1"
FILE_MOUNTINFO_CGROUP1 = DATA_PATH + "mountinfo_cgroup1"
FILE_SELF_CGROUPS_V1 = DATA_PATH + "self_cgroups_v1"

CGROUPS_FS_ROOT_MOUNT_PATH = "/sys/fs/cgroup"
CGROUPS_HOST_MOUNT_PATH = "/docker/containers/4bb4899bb7ba0e8891053352dc4a4bdbd65d038fb21f6d86673ddcd0d06e79ab"


@pytest.fixture
def all_subsys_controllers():
    return [SUBSYS_MEMORY, SUBSYS_CPU, SUBSYS_CPUACCT, SUBSYS_CPUSET, SUBSYS_PIDS]


@pytest.fixture
def all_cgroup_infos_v2(all_subsys_controllers):
    cg_infos = dict()
    for name in all_subsys_controllers:
        cg_infos[name] = CgroupInfo(name=name, hierarchy_id=0, enabled=True)
    return cg_infos


@pytest.fixture
def all_cgroup_infos_v1(all_subsys_controllers):
    cg_infos = dict()
    for name in all_subsys_controllers:
        if name == SUBSYS_PIDS:
            cg_infos[name] = CgroupInfo(name=name, hierarchy_id=12, enabled=True)
        else:
            cg_infos[name] = CgroupInfo(name=name, hierarchy_id=8, enabled=True)

    return cg_infos


def test_read_cgroup_infos_v2(all_subsys_controllers):
    assert os.path.exists(FILE_PROC_CGROUPS_V2), "file not found"
    cg_infos = _read_cgroup_infos(proc_cgroups=FILE_PROC_CGROUPS_V2, subsys_controllers=all_subsys_controllers)
    assert cg_infos is not None, "cgroup info dictionary expected"
    assert len(cg_infos) == len(all_subsys_controllers), "wrong number of entries"
    for name, cg_info in cg_infos.items():
        assert name in all_subsys_controllers, "wrong name"
        assert cg_info.enabled, "not enabled"
        assert cg_info.hierarchy_id == 0, "wrong hierarchy ID"


def test_read_cgroup_infos_v1(all_subsys_controllers):
    assert os.path.exists(FILE_PROC_CGROUPS_V1), "file not found"
    cg_infos = _read_cgroup_infos(proc_cgroups=FILE_PROC_CGROUPS_V1, subsys_controllers=all_subsys_controllers)
    assert cg_infos is not None, "cgroup info dictionary expected"
    assert len(cg_infos) == len(all_subsys_controllers), "wrong number of entries"
    for name, cg_info in cg_infos.items():
        assert name in all_subsys_controllers, "wrong name"
        assert cg_info.enabled, "not enabled"
        assert cg_info.hierarchy_id > 0, "wrong hierarchy ID"


def test_read_mount_points_v2(all_cgroup_infos_v2, all_subsys_controllers):
    assert os.path.exists(FILE_MOUNTINFO_CGROUP2), "file not found"
    cgroupv2_mount_point_found, any_cgroup_mounts_found = _read_mount_points(
        proc_self_mountinfo=FILE_MOUNTINFO_CGROUP2,
        cg_infos=all_cgroup_infos_v2,
        is_cgroups_v2=True,
        subsys_controllers=all_subsys_controllers)
    assert cgroupv2_mount_point_found, "cgroup FS v2 mount point not found"
    assert any_cgroup_mounts_found, "no cgroup mounts found"

    for cg_info in all_cgroup_infos_v2.values():
        assert cg_info.mount_path == CGROUPS_FS_ROOT_MOUNT_PATH, "wrong mount path"


def test_read_mount_points_v1(all_cgroup_infos_v1, all_subsys_controllers):
    assert os.path.exists(FILE_MOUNTINFO_CGROUP1), "file not found"
    cgroupv2_mount_point_found, any_cgroup_mounts_found = _read_mount_points(
        proc_self_mountinfo=FILE_MOUNTINFO_CGROUP1,
        cg_infos=all_cgroup_infos_v1,
        is_cgroups_v2=True,
        subsys_controllers=all_subsys_controllers)
    assert not cgroupv2_mount_point_found, "cgroup FS v2 mount point is found"
    assert any_cgroup_mounts_found, "no cgroup mounts found"

    for name, cg_info in all_cgroup_infos_v1.items():
        assert cg_info.mount_path == CGROUPS_FS_ROOT_MOUNT_PATH + "/" + name, "wrong cgroup controller mount path"
        assert cg_info.root_mount_path == CGROUPS_HOST_MOUNT_PATH, "wrong host mount path"
        assert cg_info.v1_data_complete, "data is not complete"


def test_read_proc_self_cgroup_v2(all_cgroup_infos_v2):
    assert os.path.exists(FILE_SELF_CGROUPS_V2), "file not found"
    found = _read_proc_self_cgroup(proc_self_cgroup=FILE_SELF_CGROUPS_V2,
                                   cg_infos=all_cgroup_infos_v2,
                                   is_cgroups_v2=True)
    assert found, "record not found"
    for cg_info in all_cgroup_infos_v2.values():
        assert cg_info.cgroup_path == "/", "wrong cgroup path"


def test_read_proc_self_cgroup_v1(all_cgroup_infos_v1):
    assert os.path.exists(FILE_SELF_CGROUPS_V1), "file not found"
    found = _read_proc_self_cgroup(proc_self_cgroup=FILE_SELF_CGROUPS_V1,
                                   cg_infos=all_cgroup_infos_v1,
                                   is_cgroups_v2=False)
    assert found, "record not found"
    for cg_info in all_cgroup_infos_v1.values():
        assert cg_info.cgroup_path == CGROUPS_HOST_MOUNT_PATH, "wrong cgroup path"


def test_determine_type_v2():
    sub_system = determine_type(proc_cgroups=FILE_PROC_CGROUPS_V2,
                                proc_self_cgroup=FILE_SELF_CGROUPS_V2,
                                proc_self_mountinfo=FILE_MOUNTINFO_CGROUP2)
    assert sub_system is not None, "failed to determine subsystem"
    group_type, cg_infos = sub_system
    assert group_type == CGROUP_TYPE_V2, "wrong cgroup type detected"
    assert len(cg_infos) == 5, "wrong number of controllers found"


def test_determine_type_v1():
    sub_system = determine_type(proc_cgroups=FILE_PROC_CGROUPS_V1,
                                proc_self_cgroup=FILE_SELF_CGROUPS_V1,
                                proc_self_mountinfo=FILE_MOUNTINFO_CGROUP1)
    assert sub_system is not None, "failed to determine subsystem"
    group_type, cg_infos = sub_system
    assert group_type == CGROUP_TYPE_V1, "wrong cgroup type detected"
    assert len(cg_infos) == 5, "wrong number of controllers found"


def test_build_cgroup_subsystem_v2():
    sub_system = build_cgroup_subsystem(proc_cgroups=FILE_PROC_CGROUPS_V2,
                                        proc_self_cgroup=FILE_SELF_CGROUPS_V2,
                                        proc_self_mountinfo=FILE_MOUNTINFO_CGROUP2)
    assert sub_system is not None, "failed to build subsystem"
    assert isinstance(sub_system, CgroupV2Subsystem), "wrong subsystem instance"
    assert sub_system.unified is not None, "unified controller not set"
    assert isinstance(sub_system.unified, CgroupV2Controller), "wrong controller instance"


def test_build_cgroup_subsystem_v1():
    sub_system = build_cgroup_subsystem(proc_cgroups=FILE_PROC_CGROUPS_V1,
                                        proc_self_cgroup=FILE_SELF_CGROUPS_V1,
                                        proc_self_mountinfo=FILE_MOUNTINFO_CGROUP1)
    assert sub_system is not None, "failed to build subsystem"
    assert isinstance(sub_system, CgroupV1Subsystem), "wrong subsystem instance"
    assert sub_system.cpu is not None
    assert isinstance(sub_system.cpu, CgroupV1Controller)
    assert sub_system.memory is not None
    assert isinstance(sub_system.memory, CgroupV1MemoryController)
    assert sub_system.cpuset is not None
    assert isinstance(sub_system.cpuset, CgroupV1Controller)
    assert sub_system.cpuacct is not None
    assert isinstance(sub_system.cpuacct, CgroupV1Controller)
    assert sub_system.pids is not None
    assert isinstance(sub_system.pids, CgroupV1Controller)
