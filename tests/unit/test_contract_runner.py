"""A skipped or incomplete suite must never look like a passing live gate."""

import xml.etree.ElementTree as ET

import pytest
from deploy.hindsight.contract import verify_report


def report(names, **attributes):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    for name in names:
        case = ET.SubElement(suite, "testcase", name=name)
        if name in attributes:
            ET.SubElement(case, attributes[name])
    return root


NAMES = [
    "test_default_replace_preserves_stable_identity",
    "test_async_retry_does_not_extract_twice",
    "test_original_timestamps_drive_temporal_retrieval",
    "test_never_written_bank_read_is_404",
] + [
    f"test_tag_membership[{mode}-expected{i}]"
    for i, mode in enumerate(["any", "all", "any_strict", "all_strict", "exact"])
]


def test_complete_report_passes():
    verify_report(report(NAMES))


@pytest.mark.parametrize("bad", [[], NAMES[:-1], ["test_unrelated"]])
def test_missing_contract_cannot_pass(bad):
    with pytest.raises(ValueError):
        verify_report(report(bad))


@pytest.mark.parametrize("outcome", ["skipped", "failure", "error"])
def test_nonpassing_case_cannot_pass(outcome):
    with pytest.raises(ValueError):
        verify_report(report(NAMES, **{NAMES[0]: outcome}))
