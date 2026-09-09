import asyncio
import contextvars
import gc
import unittest

from dispatcher import Signal, receiver


class SignalTests(unittest.TestCase):
    def test_caching_is_disabled_by_default(self):
        signal = Signal()

        self.assertFalse(signal.use_caching)
        self.assertIsNone(signal._sender_receivers_cache)

    def test_receiver_lookups_can_be_cached(self):
        class Sender:
            pass

        signal = Signal(use_caching=True)
        sender = Sender()

        def first_receiver(**kwargs):
            return "first"

        def second_receiver(**kwargs):
            return "second"

        signal.connect(first_receiver, sender=sender, weak=False)
        self.assertEqual(signal.send(sender), [(first_receiver, "first")])
        self.assertIn(sender, signal._sender_receivers_cache)

        signal.connect(second_receiver, sender=sender, weak=False)
        self.assertNotIn(sender, signal._sender_receivers_cache)
        self.assertEqual(
            signal.send(sender),
            [(first_receiver, "first"), (second_receiver, "second")],
        )

        signal.disconnect(first_receiver, sender=sender)
        self.assertNotIn(sender, signal._sender_receivers_cache)
        self.assertEqual(signal.send(sender), [(second_receiver, "second")])

    def test_caching_supports_none_sender(self):
        signal = Signal(use_caching=True)

        def signal_receiver(**kwargs):
            return "response"

        signal.connect(signal_receiver, weak=False)

        self.assertEqual(signal.send(), [(signal_receiver, "response")])
        self.assertIsNotNone(signal._none_sender_receivers_cache)

    def test_unweakrefable_senders_bypass_cache(self):
        signal = Signal(use_caching=True)
        sender = object()

        def signal_receiver(**kwargs):
            return "response"

        signal.connect(signal_receiver, sender=sender, weak=False)

        self.assertEqual(signal.send(sender), [(signal_receiver, "response")])
        self.assertEqual(len(signal._sender_receivers_cache), 0)

    def test_dead_receiver_invalidates_cache(self):
        class Receiver:
            def __call__(self, **kwargs):
                return "response"

        signal = Signal(use_caching=True)
        receiver_instance = Receiver()
        signal.connect(receiver_instance)
        responses = signal.send()
        self.assertEqual(responses[0][1], "response")

        del responses
        del receiver_instance
        gc.collect()

        self.assertEqual(signal.send(), [])
        self.assertIsNotNone(signal._none_sender_receivers_cache)

    def test_send_calls_matching_receivers(self):
        signal = Signal()
        sender = object()
        calls = []

        def any_sender(**kwargs):
            calls.append(("any", kwargs["sender"]))
            return "any response"

        def matching_sender(**kwargs):
            calls.append(("matching", kwargs["sender"]))
            return "matching response"

        signal.connect(any_sender, weak=False)
        signal.connect(matching_sender, sender=sender, weak=False)

        responses = signal.send(sender=sender)

        self.assertEqual(
            responses,
            [
                (any_sender, "any response"),
                (matching_sender, "matching response"),
            ],
        )
        self.assertEqual(calls, [("any", sender), ("matching", sender)])

    def test_sender_collection_removes_receiver(self):
        class Sender:
            pass

        signal = Signal()
        sender = Sender()
        signal.connect(lambda **kwargs: None, sender=sender, weak=False)

        del sender
        gc.collect()

        self.assertFalse(signal.has_listeners())
        self.assertEqual(signal._receivers, [])

    def test_robust_send_returns_exception(self):
        signal = Signal()

        def failing_receiver(**kwargs):
            raise ValueError("broken")

        signal.connect(failing_receiver, weak=False)

        responses = signal.send_robust()

        self.assertIs(responses[0][0], failing_receiver)
        self.assertIsInstance(responses[0][1], ValueError)

    def test_receiver_decorator(self):
        signal = Signal()

        @receiver(signal, weak=False)
        def decorated(**kwargs):
            return kwargs["value"]

        self.assertEqual(signal.send(value=3), [(decorated, 3)])


class AsyncSignalTests(unittest.IsolatedAsyncioTestCase):
    async def test_asend_runs_sync_receivers_before_async_receivers(self):
        signal = Signal()
        calls = []

        def sync_receiver(**kwargs):
            calls.append("sync")

        async def async_receiver(**kwargs):
            calls.append("async")

        signal.connect(async_receiver, weak=False)
        signal.connect(sync_receiver, weak=False)

        await signal.asend()

        self.assertEqual(calls, ["sync", "async"])

    async def test_async_receivers_share_context(self):
        signal = Signal()
        value = contextvars.ContextVar("value", default="initial")

        async def first_receiver(**kwargs):
            value.set("updated")

        async def second_receiver(**kwargs):
            await asyncio.sleep(0)
            return value.get()

        signal.connect(first_receiver, weak=False)
        signal.connect(second_receiver, weak=False)

        responses = await signal.asend()

        self.assertEqual(responses[1][1], "updated")
        self.assertEqual(value.get(), "updated")


if __name__ == "__main__":
    unittest.main()
