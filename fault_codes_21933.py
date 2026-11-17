"""Compatibility exports; the CMM fault catalogue lives in BITE.py."""

from BITE import FAULT_CODE_NAMES, STATUS_CODES, describe_fault_code

__all__ = ['FAULT_CODE_NAMES', 'STATUS_CODES', 'describe_fault_code']
