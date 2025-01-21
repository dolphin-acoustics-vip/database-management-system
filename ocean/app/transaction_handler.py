# transaction.py
from .models import File
from .filespace_handler import action_to_be_deleted
from contextlib import contextmanager
from .database_handler import get_session


@contextmanager
def atomic():
    with get_session() as session:
        try:
            session.begin()
            yield session
            session.commit()
            action_to_be_deleted(session)
            session.commit()
        except Exception:
            session.rollback()
            raise

@contextmanager
def atomic_with_filespace():
    """
    A context manager that provides atomicity between the database and the file space. 
    In the event of an error in either the database or the file space, all changes to
    both will be rolled back. Whenever a file is created or updated it needs to be
    tracked by the transaction proxy object that is supplied by the context manager.
    Typical usage is shown below. ::

        with atomic_with_filespace() as transaction_proxy:
            seesion = self.session
            # to create a new file and track it in the atomic session
            file = transaction_proxy.create_tracked_file()
            # to add an existing file to be tracked in the atomic session
            transaction_proxy.track_file(file)
    """

    class TransactionProxy:
        def __init__(self, session):
            self.files = []
            self.session = session
            self.on_success = None

        def track_file(self, file):
            if file:
                self.session.add(file)
                self.files.append(file)

        def create_tracked_file(self):
            file = File()
            self.track_file(file)
            return file

        def rollback(self):
            self.session.rollback()
            for file in self.files:
                file.rollback(self.session)

    with get_session() as session:
        transaction_proxy = TransactionProxy(session)
        try:
            session.begin()
            yield transaction_proxy
            session.commit()
            action_to_be_deleted(session)
            session.commit()
        except Exception:
            transaction_proxy.rollback()
            raise
        if transaction_proxy.on_success: transaction_proxy.on_success()
