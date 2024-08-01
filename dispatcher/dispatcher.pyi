from collections.abc import Callable, Hashable
from typing import Any, Literal, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])

class Signal:
    def __init__(self) -> None: ...
    def connect(
        self,
        receiver: _F,
        sender: object | None = ...,
        weak: bool = ...,
        dispatch_uid: Hashable | Literal["__qualname__"] | None = ...,
    ) -> None: ...
    def disconnect(
        self,
        receiver: _F | None = ...,
        sender: object | None = ...,
        dispatch_uid: Hashable | Literal["__qualname__"] | None = ...,
    ) -> bool: ...
    def has_listeners(
        self,
        sender: object | None = ...,
    ) -> bool: ...
    def send(
        self,
        sender: Any,
        **named: Any,
    ) -> list[tuple[_F, str | None]]: ...
    async def asend(
        self,
        sender: Any,
        **named: Any,
    ) -> list[tuple[_F, str | None]]: ...
    def send_robust(
        self,
        sender: Any,
        **named: Any,
    ) -> list[tuple[_F, Exception | Any]]: ...
    async def asend_robust(
        self,
        sender: Any,
        **named: Any,
    ) -> list[tuple[_F, Exception | Any]]: ...

def receiver(
    signal: list[Signal] | tuple[Signal, ...] | Signal,
    *,
    sender: object | None = ...,
    weak: bool = ...,
    dispatch_uid: Hashable | Literal["__qualname__"] | None = ...,
) -> Callable[[_F], _F]: ...
