import logging
console = logging.getLogger(__name__)
from pybald.core.logs import default_debug_log
import collections
from pybald.core.cache import Cache
from pybald.core.templates import Template


class Config(collections.MutableMapping):
    """A dictionary that returns keys as attributes and will return
       None for missing keys."""

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __getattribute__(self, name):
        # Some sensible default?
        try:
            return super(Config, self).__getattribute__(name)
        except AttributeError:
            return self.store.get(name, None)


class Pybald(object):
    '''Application object that handles namespacing and configuring components'''
    def __init__(self, app_name, config=None, *pargs, **kargs):
        self.setup_logging()
        self.config = self.setup_default_configuration(config)
        console.debug("Starting: {0}".format(app_name))
        self.setup_cache()
        self.setup_templates()

    def setup_default_configuration(self, config):
        return Config(**config)

    def setup_logging(self):
        default_debug_log()

    def setup_cache(self):
        Cache(self)

    def setup_templates(self):
        Template(self)

    def setup_datastore(self):
        pass


