"""Receptor syslog y parsers firewall (D04)."""

from nyxar.discovery.syslog.detector import SyslogFormatDetector
from nyxar.discovery.syslog.receiver import SyslogReceiver

__all__ = ["SyslogFormatDetector", "SyslogReceiver"]
