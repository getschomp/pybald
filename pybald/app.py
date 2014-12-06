import logging
console = logging.getLogger(__name__)
from pybald.core.logs import default_debug_log

class Pybald(object):
    '''Application object that handles namespacing and configuring components'''
    def __init__(self, app_name, config=None, *pargs, **kargs):
        self.setup_logging()
        if config is None:
            # default configuration
            self.config = self.setup_default_configuration()
        console.debug("{0} {1} {2}".format(app_name, pargs, kargs))

    def setup_default_configuration(self):
        return {}

    def setup_logging(self):
        # import pybald.core
        default_debug_log()

    def setup_templates(self):
        pass

    def setup_datastore(self):
        pass


