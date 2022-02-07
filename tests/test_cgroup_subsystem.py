from unittest.mock import MagicMock

import pytest

from oscontainer import NO_LIMIT, PER_CPU_SHARES
from oscontainer.cgroup_subsystem import CgroupSubsystem

TEST_HOST_CPU_COUNT = 8


@pytest.mark.parametrize(
    "quota, period, expected",
    [
        (10000, 100000, 1),
        (100000, 100000, 1),
        (150000, 100000, 2),
        (200000, 100000, 2),
        (350000, 100000, 4)
    ]
)
def test_active_processor_count_quota(quota, period, expected):
    sub_system = CgroupSubsystem()
    sub_system.cpu_quota = MagicMock(return_value=quota)
    sub_system.cpu_period = MagicMock(return_value=period)
    sub_system.cpu_shares = MagicMock(return_value=NO_LIMIT)

    cpu_count = sub_system.active_processor_count(prefer_container_quota=True,
                                                  host_cpu_count=TEST_HOST_CPU_COUNT)
    assert cpu_count == expected, "wrong CPU count"


@pytest.mark.parametrize(
    "shares, expected",
    [
        (PER_CPU_SHARES, 1),
        (PER_CPU_SHARES * 2, 2),
        (PER_CPU_SHARES * 2.2, 3)
    ]
)
def test_active_processor_count_shares(shares, expected):
    sub_system = CgroupSubsystem()
    sub_system.cpu_quota = MagicMock(return_value=NO_LIMIT)
    sub_system.cpu_period = MagicMock(return_value=0)
    sub_system.cpu_shares = MagicMock(return_value=shares)

    cpu_count = sub_system.active_processor_count(prefer_container_quota=False,
                                                  host_cpu_count=TEST_HOST_CPU_COUNT)
    assert cpu_count == expected, "wrong CPU count"


@pytest.mark.parametrize(
    "quota, period, shares, expected",
    [
        (10000, 100000, PER_CPU_SHARES, 1),
        (100000, 100000, PER_CPU_SHARES, 1),
        (150000, 100000, PER_CPU_SHARES * 2.2, 2),
        (250000, 100000, PER_CPU_SHARES * 2.2, 3),
    ]
)
def test_active_processor_count(quota, period, shares, expected):
    sub_system = CgroupSubsystem()
    sub_system.cpu_quota = MagicMock(return_value=quota)
    sub_system.cpu_period = MagicMock(return_value=period)
    sub_system.cpu_shares = MagicMock(return_value=shares)

    cpu_count = sub_system.active_processor_count(prefer_container_quota=False,
                                                  host_cpu_count=TEST_HOST_CPU_COUNT)
    assert cpu_count == expected, "wrong CPU count"
