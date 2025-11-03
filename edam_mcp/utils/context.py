import logging

from fastmcp.server import Context


class MockContext(Context):
    def __init__(self):
        self.log = logging.getLogger(__name__)

    def info(self, msg):
        self.log.info(msg)

    def warning(self, msg):
        self.log.warning(msg)

    def debug(self, msg):
        self.log.debug(msg)

    def error(self, msg):
        self.log.error(msg)
