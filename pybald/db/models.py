import sqlalchemy
from sqlalchemy import dialects

# load sqlalchemy modules proxied through the models object
# this is mostly for convenience
from sqlalchemy import (
    MetaData,
    INT as Int,
    Integer,
    Float,
    Column,
    UniqueConstraint,
    Index,
    ForeignKey,
    String,
    DateTime,
    TIMESTAMP as TimeStamp,
    PickleType,
    Time,
    Table,
    or_,
    and_,
    not_,
    select
    )

from sqlalchemy.types import (
    BLOB,
    BOOLEAN,
    BigInteger,
    Binary,
    Boolean,
    CHAR,
    CLOB,
    DATE,
    DATETIME,
    DECIMAL,
    Date,
    DateTime,
    Enum,
    FLOAT,
    Float,
    INT,
    INTEGER,
    Integer,
    Interval,
    LargeBinary,
    NCHAR,
    NVARCHAR,
    NUMERIC,
    Numeric,
    PickleType,
    SMALLINT,
    SmallInteger,
    String,
    TEXT,
    TIME,
    TIMESTAMP,
    Text,
    Time,
    TypeDecorator,
    Unicode,
    UnicodeText,
    VARCHAR,
    )


from sqlalchemy.orm import (
    column_property,
    mapper,
    scoped_session,
    sessionmaker,
    reconstructor,
    relationship,
    backref,
    contains_eager,
    eagerload,
    eagerload_all,
    joinedload,
    synonym,
    object_session
    )

from sqlalchemy.orm.attributes import (
    instance_state
    )

from sqlalchemy.orm.util import (
    has_identity
)

from sqlalchemy.orm.exc import (
    NoResultFound,
    MultipleResultsFound
    )

from sqlalchemy.exc import (
    IntegrityError
    )

from sqlalchemy.sql import (
    exists,
    )

from sqlalchemy.sql.expression import (
    asc,
    case,
    desc,
    literal,
    literal_column,
    null
    )

from sqlalchemy.ext.hybrid import (
                    hybrid_property,
                    hybrid_method
    )

from sqlalchemy import func


from pybald.util import camel_to_underscore, pluralize

# import project
# from project import mc

# from sqlalchemy.orm.interfaces import SessionExtension
# from sqlalchemy.ext.mutable import Mutable

from sqlalchemy import __version__ as sa_ver

sa_maj_ver, sa_min_ver, sa_rev_ver = sa_ver.split(".")

if int(sa_min_ver) >= 7:
    from sqlalchemy.orm.attributes import flag_modified
else:
    from sqlalchemy.orm.attributes import instance_dict, NO_VALUE

    def flag_modified(instance, key):
        state, dict_ = instance_state(instance), instance_dict(instance)
        impl = state.manager[key].impl
        state.modified_event(dict_, impl, True, NO_VALUE)

from types import ASCII, JSONEncodedDict, ZipPickler, MutationDict
from pybald.db import engine, dump_engine

import sqlalchemy.ext.declarative
from sqlalchemy.ext.declarative import declarative_base


session_args = {}


# if project.green:
#     from SAGreen import eventlet_greenthread_scope
#     session_args['scopefunc'] = eventlet_greenthread_scope



class NotFound(NoResultFound):
    '''Generic Not Found Error'''
    pass

# using a surrogate_pk_template allows the surrogate_pk to always
# come first when defining models, which flows more naturally
# when looking at the actual database tables.
surrogate_pk_template = Column(Integer, nullable=False, primary_key=True)


class Database(object):
    def __getattribute__(self, name):
        '''Proxy requests from the config object into the module level
           load if not in the object'''
        try:
            return super(Database, self).__getattribute__(name)
        except AttributeError as original_exception:
            # if it's not in this object, see if it's in the
            # module's namespace. That would let us still use
            # this object as a convenience proxy for SA (and other)
            # methods
            try:
                return globals()[name]
            except KeyError:
                raise original_exception

    def __init__(self, app, config=None):
        # assign this object to the app
        setattr(app, 'db', self)

        session_args = {}
        engine_args = app.config.database_engine_args

        def dump(sql, *multiparams, **params):
            print str(sql.compile(dialect=dump_engine.dialect) )

        dump_engine = sqlalchemy.create_engine('mysql://', strategy='mock', executor=dump)

        try:
            engine = sqlalchemy.create_engine(app.config.database_engine_uri, **engine_args)
        except AttributeError:
            # change this to an log warning
            sys.stderr.write("**WARNING**\nSQLALchemy/pybald is using a mock"
                             " db connection.\n")
            engine = dump_engine

        session = scoped_session(sessionmaker(bind=engine, **session_args))
        Base = declarative_base(bind=engine)

        class ModelMeta(sqlalchemy.ext.declarative.DeclarativeMeta):
            '''
            MetaClass that sets up some common behaviors for pybald models.

            Will assign tablename if not defined based on pluralization rules. Also
            applies project global table arguments. Lastly this will assign a
            numeric primary key id to the table if no primary key was defined
            in the model class.
            '''
            def __init__(cls, name, bases, ns):
                try:
                    if Model not in bases:
                        # Allow for inheritance of the Model object
                        # for use with SqlAlchemy inheritance patterns
                        super(ModelMeta, cls).__init__(name, bases, ns)
                        return
                except NameError:
                    # if this is the Model class, then just return
                    return

                # set the tablename, if it's user set, use that, otherwise use a
                # function to create one
                cls.__tablename__ = getattr(cls, "__tablename__",
                                            pluralize(camel_to_underscore(name)))
                # tableargs adds autoload to create schema reflection
                cls.__table_args__ = getattr(cls, "__table_args__", {})

                if app.config.schema_reflection:
                    # create or update the __table_args__ attribute
                    cls.__table_args__['autoload'] = True
                if app.config.global_table_args:
                    cls.__table_args__.update(app.config.global_table_args)

                # check if the class has at least one primary key
                # if not, automatically generate one.
                has_primary = any([False] + [value.primary_key
                                             for value in cls.__dict__.values()
                                             if isinstance(value, Column)])
                if not has_primary:
                    # treat the id as a mixin w/copy
                    surrogate_pk = surrogate_pk_template.copy()
                    surrogate_pk._creation_order = surrogate_pk_template._creation_order
                    cls.id = surrogate_pk
                super(ModelMeta, cls).__init__(name, bases, ns)


        class RegistryMount(type):
            '''
            A registry creating metaclass that keeps track of all defined classes that
            inherit from a base class using this metaclass.
            '''
            # lifted almost verbatim from: http://martyalchin.com/2008/jan/10/simple-plugin-framework/
            def __init__(cls, name, bases, attrs):
                try:
                    cls.registry.append(cls)
                except AttributeError:
                    # this is processing the first class (the mount point)
                    cls.registry = []

                return super(RegistryMount, cls).__init__(name, bases, attrs)


        class RegistryModelMeta(RegistryMount, ModelMeta):
            pass


        class Model(Base):
            '''Pybald Model class, inherits from SQLAlchemy Declarative Base.'''
            __metaclass__ = RegistryModelMeta

            NotFound = sqlalchemy.orm.exc.NoResultFound
            MultipleFound = sqlalchemy.orm.exc.MultipleResultsFound

            def is_modified(self):
                '''Check if SQLAlchemy believes this instance is modified.'''
                # TODO: Using this internal flag, is this a private internal
                # behavior? Is there a better, public-api way of getting this info?
                # alternatively is session.is_modified(self) although will this fail
                # if the instance isn't part of the session?
                return instance_state(self).modified

            def clear_modified(self):
                '''
                Unconditionally clear all modified state from the attibutes on
                this instance.
                '''
                # Uses this method: http://www.sqlalchemy.org/docs/orm/internals.html?highlight=commit_all#sqlalchemy.orm.state.InstanceState.commit_all
                if int(sa_min_ver) > 7:
                    # the methods became private in SA 8, need to check if
                    # this is a problem
                    return instance_state(self)._commit_all({})
                else:
                    return instance_state(self).commit_all({})

            def is_persisted(self):
                '''
                Check if this instance has ever been persisted. Means it is either
                `detached` or `persistent`.
                '''
                return has_identity(self)

            def save(self, flush=False):
                '''
                Saves (adds) this instance in the current databse session.

                This does not immediatly persist the data since these operations
                occur within a transaction and the sqlalchemy unit-of-work pattern.
                If something causes a rollback before the session is committed,
                these changes will be lost.

                When flush is `True`, flushes the data to the database immediately
                **within the same transaction**. This does not commit the transaction,
                for that use :py:meth:`~pybald.db.models.Model.commit`)
                '''

                session.add(self)

                if flush:
                    self.flush()
                return self

            def delete(self, flush=False):
                '''
                Delete this instance from the current database session.

                The object will be deleted from the database at the next commit. If
                you want to immediately delete the object, you should follow this
                operation with a commit to emit the SQL to delete the item from
                the database and commit the transaction.
                '''
                session.delete(self)
                if flush:
                    self.flush()
                return self

            def flush(self):
                '''
                Syncs all pending SQL changes (including other pending objects) to
                the underlying data store within the current transaction.

                Flush emits all the relevant SQL to the underlying store, but does
                **not** commit the current transaction or close the current
                database session.
                '''
                session.flush()
                return self

            def commit(self):
                '''
                Commits the entire database session (including other pending objects).

                This emits all relevant SQL to the databse, commits the current
                transaction, and closes the current session (and database connection)
                and returns it to the connection pool. Any data operations after this
                will pull a new database session from the connection pool.
                '''
                session.commit()
                return self

            @classmethod
            def get(cls, **where):
                '''
                A convenience method that constructs a load query with keyword
                arguments as the filter arguments and return a single instance.
                '''
                return cls.load(**where).one()

            @classmethod
            def all(cls, **where):
                '''
                Returns a collection of objects that can be filtered for
                specific collections.

                all() without arguments returns all the items of the model type.
                '''
                return cls.load(**where).all()

            # methods that return queries (must execute to retrieve)
            # =============================================================
            @classmethod
            def load(cls, **where):
                '''
                Convenience method to build a sqlalchemy query to return stored
                objects.

                Returns a query object. This query object must be executed to retrieve
                actual items from the database.
                '''
                if where:
                    return session.query(cls).filter_by(**where)
                else:
                    return session.query(cls)

            @classmethod
            def filter(cls, *pargs, **kargs):
                '''
                Convenience method that auto-builds the query and passes the filter
                to it.

                Returns a query object.
                '''
                return session.query(cls).filter(*pargs, **kargs)

            @classmethod
            def query(cls):
                '''
                Convenience method to return a query based on the current object
                class.
                '''
                return session.query(cls)

            @classmethod
            def show_create_table(cls):
                '''
                Uses the simple dump_engine to print to stdout the SQL for this
                table.
                '''
                cls.__table__.create(dump_engine)


        class NonDbModel(object):
            '''
            A plain Python object that uses the RegistryMount system to register
            non database models. Inheriting from this allows the object to be registered
            as a Model.
            '''
            __metaclass__ = RegistryMount
            # use the same registry space for NonDbModels
            registry = Model.registry

        # surface the classes for use
        self.Model = Model
        self.NonDbModel = NonDbModel
