"""dispatcher module adapted from django."""

from __future__ import annotations

import asyncio
import threading
import weakref

from asgiref.sync import async_to_sync, iscoroutinefunction, sync_to_async

__all__ = [
    "Signal",
]


def _make_id(target):
    if (
        (target is not None)
        and hasattr(target, "__self__")
        and hasattr(target, "__func__")
    ):
        return (id(target.__self__), id(target.__func__))
    else:
        return (id(target), id(target))


NONEKEY = _make_id(target=None)


def _create_lookup_key(
    receiver,
    sender,
    dispatch_uid,
):
    """Create lookup key.

    :param receiver: A function or an instance method which is to receive signals. Receivers must be hashable objects. Receivers can be asynchronous.
    :param sender: The sender to which the receiver should respond. Must either be a Python object, or None to receive events from any sender.
    :param dispatch_uid: An identifier used to uniquely identify a particular instance of a receiver. This will usually be a string, though it may be anything hashable. If set to ``__qualname__``, ``receiver.__qualname__`` will be used.

    :return: The lookup key.
    """
    rkey = _make_id(target=receiver)
    if dispatch_uid == "__qualname__":
        if (receiver is not None) and hasattr(receiver, "__qualname__"):
            rkey = receiver.__qualname__
    elif dispatch_uid is not None:
        rkey = dispatch_uid
    return (rkey, _make_id(target=sender))


class Signal:
    """Base class for all signals.

    Internal attributes:
        receivers
            { receiverkey (id) : weakref(receiver) }
    """

    def __init__(self):
        """Construct the instance."""
        self._receivers = []
        self._lock = threading.Lock()
        self._dead_receivers = False

    def connect(
        self,
        receiver,
        sender=None,
        weak=True,
        dispatch_uid=None,
    ):
        """Connect receiver to sender for signal.

        :param receiver: A function or an instance method which is to receive signals. Receivers must be hashable objects. Receivers can be asynchronous.
        :param sender: The sender to which the receiver should respond. Must either be a Python object, or None to receive events from any sender.
        :param weak: Whether to use weak references to the receiver. By default, the module will attempt to use weak references to the receiver objects. If this parameter is false, then strong references will be used.
        :param dispatch_uid: An identifier used to uniquely identify a particular instance of a receiver. This will usually be a string, though it may be anything hashable. If set to ``__qualname__``, ``receiver.__qualname__`` will be used.
        """
        lookup_key = _create_lookup_key(
            receiver=receiver,
            sender=sender,
            dispatch_uid=dispatch_uid,
        )

        is_async = iscoroutinefunction(func=receiver)

        if weak:
            # Check for bound methods
            if hasattr(receiver, "__self__") and hasattr(receiver, "__func__"):
                receiver_ = weakref.WeakMethod(receiver)
                weakref.finalize(receiver.__self__, self._remove_receiver)
            else:
                receiver_ = weakref.ref(receiver)
                weakref.finalize(receiver, self._remove_receiver)
        else:
            receiver_ = receiver

        with self._lock:
            self._clear_dead_receivers()
            if not any(_key == lookup_key for _key, _, _ in self._receivers):
                self._receivers.append((lookup_key, receiver_, is_async))

    def disconnect(
        self,
        receiver=None,
        sender=None,
        dispatch_uid=None,
    ):
        """Disconnect receiver from sender for signal.

        :param receiver: A function or an instance method which is to receive signals. Receivers must be hashable objects. Receivers can be asynchronous.
        :param sender: The sender to which the receiver should respond. Must either be a Python object, or None to receive events from any sender.
        :param dispatch_uid: An identifier used to uniquely identify a particular instance of a receiver. This will usually be a string, though it may be anything hashable. If set to ``__qualname__``, ``receiver.__qualname__`` will be used.

        :return: Whether the receiver has been disconnected.

        If weak references are used, disconnect need not be called. The receiver will be removed from dispatch automatically.
        """
        lookup_key = _create_lookup_key(
            receiver=receiver,
            sender=sender,
            dispatch_uid=dispatch_uid,
        )

        disconnected = False
        with self._lock:
            self._clear_dead_receivers()
            for index in range(len(self._receivers)):
                r_key, *_ = self._receivers[index]
                if r_key == lookup_key:
                    disconnected = True
                    del self._receivers[index]
                    break
        return disconnected

    def has_listeners(
        self,
        sender=None,
    ):
        """Check if sender has any listener.

        :param sender: The sender to which the receiver should respond. Must either be a Python object, or None to receive events from any sender.

        :return: Whether the sender has any listeners.
        """
        sync_receivers, async_receivers = self._live_receivers(sender=sender)
        return bool(sync_receivers) or bool(async_receivers)

    def send(self, sender=None, **named):
        """Send signal from sender to all connected receivers.

        :param sender: The sender to which the receiver should respond. Must either be a Python object, or None to receive events from any sender.
        :param named: Named arguments which will be passed to receivers.

        :return: The list of (receiver, response) tuple.
        """
        responses = []
        if not self._receivers:
            return responses
        sync_receivers, async_receivers = self._live_receivers(sender=sender)
        for receiver in sync_receivers:
            response = receiver(signal=self, sender=sender, **named)
            responses.append((receiver, response))
        if async_receivers:

            async def asend():
                async_responses = await asyncio.gather(
                    *(
                        receiver(signal=self, sender=sender, **named)
                        for receiver in async_receivers
                    )
                )
                return zip(async_receivers, async_responses, strict=False)

            responses.extend(async_to_sync(awaitable=asend)())
        return responses

    async def asend(self, sender=None, **named):
        """Send signal from sender to all connected receivers in async mode.

        :param sender: The sender to which the receiver should respond. Must either be a Python object, or None to receive events from any sender.
        :param named: Named arguments which will be passed to receivers.

        :return: The list of (receiver, response) tuple.


        All sync receivers will be wrapped by sync_to_async(). If any receiver raises an error, the error propagates back through send,
        terminating the dispatch loop. So it's possible that all receivers won't be called if an error is raised.

        If any receivers are synchronous, they are grouped and called behind a sync_to_async() adaption before executing any asynchronous receivers.

        If any receivers are asynchronous, they are grouped and executed concurrently with asyncio.gather().
        """
        responses = []
        if not self._receivers:
            return responses
        sync_receivers, async_receivers = self._live_receivers(sender=sender)
        if sync_receivers:

            @sync_to_async
            def sync_send():
                responses = []
                for receiver in sync_receivers:
                    response = receiver(signal=self, sender=sender, **named)
                    responses.append((receiver, response))
                return responses
        else:

            async def sync_send():
                return []

        responses, async_responses = await asyncio.gather(
            sync_send(),
            asyncio.gather(
                *(
                    receiver(signal=self, sender=sender, **named)
                    for receiver in async_receivers
                )
            ),
        )
        responses.extend(zip(async_receivers, async_responses, strict=False))
        return responses

    def _log_robust_failure(self, receiver, err):
        # logger.error(
        #     "Error calling %s in Signal.send_robust() (%s)",
        #     receiver.__qualname__,
        #     err,
        #     exc_info=err,
        # )
        pass

    def send_robust(self, sender=None, **named):
        """Send signal from sender to all connected receivers catching errors.

        :param sender: The sender to which the receiver should respond. Must either be a Python object, or None to receive events from any sender.
        :param named: Named arguments which will be passed to receivers.

        :return: The list of (receiver, response or Exception) tuple.


        If any receivers are asynchronous, they are called after all the synchronous receivers via a single call to async_to_sync(). They are also executed concurrently with asyncio.gather().
        """
        responses = []
        if not self._receivers:
            return responses
        sync_receivers, async_receivers = self._live_receivers(sender=sender)
        for receiver in sync_receivers:
            try:
                response = receiver(signal=self, sender=sender, **named)
            except Exception as err:
                self._log_robust_failure(receiver=receiver, err=err)
                responses.append((receiver, err))
            else:
                responses.append((receiver, response))
        if async_receivers:

            async def asend_and_wrap_exception(receiver):
                try:
                    response = await receiver(signal=self, sender=sender, **named)
                except Exception as err:
                    self._log_robust_failure(receiver=receiver, err=err)
                    return err
                return response

            async def asend():
                async_responses = await asyncio.gather(
                    *(
                        asend_and_wrap_exception(receiver=receiver)
                        for receiver in async_receivers
                    )
                )
                return zip(async_receivers, async_responses, strict=False)

            responses.extend(async_to_sync(awaitable=asend)())
        return responses

    async def asend_robust(self, sender=None, **named):
        """Asynchronously send signal from sender to all connected receivers catching errors.

        :param sender: The sender to which the receiver should respond. Must either be a Python object, or None to receive events from any sender.
        :param named: Named arguments which will be passed to receivers.

        :return: The list of (receiver, response or Exception) tuple.


        If any receivers are synchronous, they are grouped and called behind a sync_to_async() adaption before executing any asynchronous receivers.

        If any receivers are asynchronous, they are grouped and executed concurrently with asyncio.gather.
        """
        responses = []
        if not self._receivers:
            return responses
        sync_receivers, async_receivers = self._live_receivers(sender=sender)

        if sync_receivers:

            @sync_to_async
            def sync_send():
                responses_ = []
                for receiver in sync_receivers:
                    try:
                        response = receiver(signal=self, sender=sender, **named)
                    except Exception as err:
                        self._log_robust_failure(receiver=receiver, err=err)
                        responses_.append((receiver, err))
                    else:
                        responses_.append((receiver, response))
                return responses_

        else:

            async def sync_send():
                return []

        async def asend_and_wrap_exception(receiver):
            try:
                response = await receiver(signal=self, sender=sender, **named)
            except Exception as err:
                self._log_robust_failure(receiver, err)
                return err
            return response

        responses, async_responses = await asyncio.gather(
            sync_send(),
            asyncio.gather(
                *(
                    asend_and_wrap_exception(receiver=receiver)
                    for receiver in async_receivers
                ),
            ),
        )
        responses.extend(zip(async_receivers, async_responses, strict=False))
        return responses

    def _clear_dead_receivers(self):
        """Remove dead receivers.

        Note: caller is assumed to hold self._lock.
        """
        if self._dead_receivers:
            self._dead_receivers = False
            self._receivers = [
                (k, r, ia)
                for (k, r, ia) in self._receivers
                if not (
                    isinstance(r, (weakref.ReferenceType, weakref.WeakMethod))
                    and (r() is None)
                )
            ]

    def _live_receivers(self, sender=None):
        """Filter sequence of receivers to get resolved, live receivers.

        :param sender: The sender of the signal.

        :return: The decorated function.

        This checks for weak references and resolves them, then returning only live receivers.
        """
        receivers = []
        with self._lock:
            self._clear_dead_receivers()
            senderkey = _make_id(target=sender)
            for (__, _senderkey), receiver, is_async in self._receivers:
                if _senderkey == NONEKEY or _senderkey == senderkey:
                    receivers.append((receiver, is_async))
        non_weak_sync_receivers = []
        non_weak_async_receivers = []
        for receiver, is_async in receivers:
            if isinstance(receiver, (weakref.ReferenceType, weakref.WeakMethod)):
                # Dereference the weak reference.
                receiver_ = receiver()
                if receiver_ is not None:
                    if is_async:
                        non_weak_async_receivers.append(receiver_)
                    else:
                        non_weak_sync_receivers.append(receiver_)
            else:
                if is_async:
                    non_weak_async_receivers.append(receiver)
                else:
                    non_weak_sync_receivers.append(receiver)
        return non_weak_sync_receivers, non_weak_async_receivers

    def _remove_receiver(self, receiver=None):
        """Mark that the self._receivers list has dead weakrefs.

        :param signal: The signal or list of signals.
        :param sender: The signal or list of signals.
        :param weak: The signal or list of signals.
        :param dispatch_uid: The signal or list of signals.

        If so, we will clean those up in connect, disconnect and _live_receivers while holding self._lock.
        Note that doing the cleanup here isn't a good idea, _remove_receiver() will be called
        as side effect of garbage collection, and so the call can happen while we are already holding self._lock.
        """
        self._dead_receivers = True


def receiver(signal, *, sender=None, weak=True, dispatch_uid=None):
    """Decorate function for connecting receivers to signals.

    :param signal: The signal or list of signals.
    :param sender: The sender to which the receiver should respond. Must either be a Python object, or None to receive events from any sender.
    :param weak: Whether to use weak references to the receiver. By default, the module will attempt to use weak references to the receiver objects. If this parameter is false, then strong references will be used.
    :param dispatch_uid: An identifier used to uniquely identify a particular instance of a receiver. This will usually be a string, though it may be anything hashable.

    :return: The decorated function.


    Here are a few examples:

        @receiver(post_save, sender=MyModel)
        def signal_receiver(sender, **kwargs): ...


        @receiver([post_save, post_delete])
        def signals_receiver(sender, **kwargs): ...
    """

    def _decorator(func):
        if isinstance(signal, (list, tuple)):
            for s in signal:
                s.connect(
                    receiver=func,
                    sender=sender,
                    weak=weak,
                    dispatch_uid=dispatch_uid,
                )
        else:
            signal.connect(
                receiver=func,
                sender=sender,
                weak=weak,
                dispatch_uid=dispatch_uid,
            )
        return func

    return _decorator
