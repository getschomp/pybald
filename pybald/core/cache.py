import memcache
class Cache(object):
    def __init__(self, app, config=None):
        if config is None:
            config = {}
        registered_as = "mc"
        memcached_clients = ['127.0.0.1:11211']
        mc = memcache.Client(memcached_clients, debug=0)
        setattr(app, registered_as, mc)
