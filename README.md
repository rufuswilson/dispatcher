# dispatcher


Changes
---------

* Caching is optional and disabled by default.
* Removed logging.
* Formatted docstrings.
* Added type stub.

This version requires Python 3.11 or newer.


Caching
---------
Caching is disabled by default. It can improve performance when a signal is
sent frequently by the same sender and its receivers rarely change. Enable it
when creating the signal:

```python
from dispatcher import Signal

signal = Signal(use_caching=True)
```

The cache is cleared whenever a receiver is connected, disconnected, or
garbage-collected.

If a sender cannot safely be used as a cache key, signal delivery still works;
the library looks up its receivers each time instead.


Last pulled
-------------
https://github.com/django/django/blob/main/django/dispatch/dispatcher.py
Last commit: ba4751e
Date commit: 17/03/2026
