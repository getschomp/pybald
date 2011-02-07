
from webob import Request,Response

from app.models import User
class UserManager(object):
    '''Code to handle anonymous and user sessions, implemented as WSGI middleware.'''

    def __init__(self,application=None):
        if application:
            self.application = application
        else:
            # no pipeline so just generate a generic response
            self.applicaion = Response()

    def __call__(self,environ,start_response):
        req = Request(environ)

        session = environ.get('pybald.session', None)
        if session and session.user_id:
                if session.user:
                    environ['REMOTE_USER'] = session.user
                else:
                    try:
                        environ['REMOTE_USER'] = User.get(id=session.user_id)
                    except User.NotFound:
                        environ['REMOTE_USER'] = None
        else:
            environ['REMOTE_USER'] = None

        if not environ.has_key('pybald.extension'):
            environ['pybald.extension'] = {}
        environ['pybald.extension']['user'] = environ['REMOTE_USER']



        # call the next part of the pipeline
        resp = req.get_response(self.application)
        return resp(environ,start_response)