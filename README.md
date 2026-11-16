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


Upstream provenance
-------------------
The implementation was last synchronized on 17 March 2026 from
[Django's dispatcher module](https://github.com/django/django/blob/ba4751e0ca558dd8f0d9e6153bec4280289ca2f4/django/dispatch/dispatcher.py),
at commit `ba4751e0ca558dd8f0d9e6153bec4280289ca2f4` (authored 23 February
2026).

The project is distributed under the BSD 3-Clause License. See
[LICENSE](LICENSE) and [dispatcher/license.txt](dispatcher/license.txt) for the
Django and original PyDispatcher notices.
