"""Transactional outbox.

The outbox turns the DB+stream *dual-write* into a single atomic DB write:
the domain change and the event row are inserted in the same transaction,
so they commit or roll back together. A separate relay process then reads
unpublished rows and pushes them to the real stream (at-least-once).

    OutboxEventProducer -> EventProducer that writes an event row into the
                           caller's session (no external I/O).
    OutboxEventORM      -> the `outbox_events` table.
    OutboxRelay         -> polls unpublished rows and publishes them.
"""
