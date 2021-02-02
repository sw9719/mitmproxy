import time
import typing  # noqa
import uuid

from mitmproxy import controller, connection
from mitmproxy import exceptions
from mitmproxy import stateobject
from mitmproxy import version


class Error(stateobject.StateObject):
    """
        An Error.

        This is distinct from an protocol error response (say, a HTTP code 500),
        which is represented by a normal `mitmproxy.http.Response` object. This class is
        responsible for indicating errors that fall outside of normal protocol
        communications, like interrupted connections, timeouts, protocol errors.
    """

    msg: str
    """Message describing the error."""

    timestamp: float
    """Unix timestamp"""

    KILLED_MESSAGE = "Connection killed."

    def __init__(self, msg: str, timestamp: typing.Optional[float] = None) -> None:
        """Create an error. If no timestamp is passed, the current time is used."""
        self.msg = msg
        self.timestamp = timestamp or time.time()

    _stateobject_attributes = dict(
        msg=str,
        timestamp=float
    )

    def __str__(self):
        return self.msg

    def __repr__(self):
        return self.msg

    @classmethod
    def from_state(cls, state):
        # the default implementation assumes an empty constructor. Override
        # accordingly.
        f = cls(None)
        f.set_state(state)
        return f


class Flow(stateobject.StateObject):
    """
    A Flow is a collection of objects representing a single transaction.
    This class is usually subclassed for each protocol, e.g. HTTPFlow.
    """

    def __init__(
        self,
        type: str,
        client_conn: connection.Client,
        server_conn: connection.Server,
        live: bool = None
    ) -> None:
        self.type = type
        self.id = str(uuid.uuid4())
        self.client_conn = client_conn
        self.server_conn = server_conn
        self.live = live

        self.error: typing.Optional[Error] = None
        self.intercepted: bool = False
        self._backup: typing.Optional[Flow] = None
        self.reply: typing.Optional[controller.Reply] = None
        self.marked: bool = False
        self.is_replay: typing.Optional[str] = None
        self.metadata: typing.Dict[str, typing.Any] = dict()

    _stateobject_attributes = dict(
        id=str,
        error=Error,
        client_conn=connection.Client,
        server_conn=connection.Server,
        type=str,
        intercepted=bool,
        is_replay=str,
        marked=bool,
        metadata=typing.Dict[str, typing.Any],
    )

    def get_state(self):
        d = super().get_state()
        d.update(version=version.FLOW_FORMAT_VERSION)
        if self._backup and self._backup != d:
            d.update(backup=self._backup)
        return d

    def set_state(self, state):
        state = state.copy()
        state.pop("version")
        if "backup" in state:
            self._backup = state.pop("backup")
        super().set_state(state)

    @classmethod
    def from_state(cls, state):
        f = cls(None, None)
        f.set_state(state)
        return f

    def copy(self):
        f = super().copy()
        f.live = False
        if self.reply is not None:
            f.reply = controller.DummyReply()
        return f

    def modified(self):
        """
            Has this Flow been modified?
        """
        if self._backup:
            return self._backup != self.get_state()
        else:
            return False

    def backup(self, force=False):
        """
            Save a backup of this Flow, which can be reverted to using a
            call to .revert().
        """
        if not self._backup:
            self._backup = self.get_state()

    def revert(self):
        """
            Revert to the last backed up state.
        """
        if self._backup:
            self.set_state(self._backup)
            self._backup = None

    @property
    def killable(self):
        return (
            self.reply and
            self.reply.state in {"start", "taken"} and
            not (self.error and self.error.msg == Error.KILLED_MESSAGE)
        )

    def kill(self):
        """
            Kill this request.
        """
        if not self.killable:
            raise exceptions.ControlException("Flow is not killable.")
        self.error = Error(Error.KILLED_MESSAGE)
        self.intercepted = False
        self.live = False

    def intercept(self):
        """
            Intercept this Flow. Processing will stop until resume is
            called.
        """
        if self.intercepted:
            return
        self.intercepted = True
        self.reply.take()

    def resume(self):
        """
            Continue with the flow - called after an intercept().
        """
        if not self.intercepted:
            return
        self.intercepted = False
        # If a flow is intercepted and then duplicated, the duplicated one is not taken.
        if self.reply.state == "taken":
            self.reply.commit()

    @property
    def timestamp_start(self) -> float:
        """Start time of the flow."""
        return self.client_conn.timestamp_start


__all__ = [
    "Flow",
    "Error",
]
