"""
Simple counters that keep track of how often certain Mutalyzer functionality
is used. Backed by Redis.

For a given counter, we maintain the total count and the count per minute,
hour, and day. The total count is maintained indefinite, the others
automatically expire after some predefined time.

.. todo:: Implement querying of counters and building a simple dashboard-like
    user inteface for live viewing of the counters. Have a look at `this post
    <http://stackoverflow.com/questions/10155398/getting-multiple-key-values-from-redis>`
    for some possible implementation ideas.

We might want to consider using something like `Kairos
<https://github.com/agoragames/kairos>`_ instead of growing on top of this
module much more.
"""


from __future__ import unicode_literals

import time

from .redisclient import client as redis


# Label, bucket definition, expiration time in seconds.
INTERVALS = [('minute', '%Y-%m-%d_%H:%M', 60 * 60),
             ('hour', '%Y-%m-%d_%H', 60 * 60 * 24),
             ('day', '%Y-%m-%d', 60 * 60 * 24 * 30)]


def increment_counter(counter):
    """
    Increment the specified counter.
    """
    pipe = redis.pipeline(transaction=False)
    pipe.incr('counter:%s:total' % counter)

    for label, bucket, expire in INTERVALS:
        key = 'counter:%s:%s:%s' % (counter, label,
                                    unicode(time.strftime(bucket)))
        pipe.incr(key)

        # It's safe to just keep on expiring the counter, even if it already
        # had an expiration, since it is bounded by the current day. We don't
        # really mind at what time of the day the expiration will be exactly.
        pipe.expire(key, expire)

    pipe.execute()


def get_totals():
    """
    Get the total for all known counters.

    Known counters are just those that have been incremented at least once.
    """
    counters = redis.keys('counter:*:total')

    pipe = redis.pipeline(transaction=False)
    for counter in counters:
        pipe.get(counter)

    return {counter.split(':')[1]: int(value)
            for counter, value in zip(counters, pipe.execute())}
