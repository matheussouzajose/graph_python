"""Shared names for streams and event types.

Keeping these in one place avoids typos between producer and consumer
(a mismatched stream name = silently no messages delivered).
"""

# Stream (queue/topic) that carries video lifecycle events.
VIDEO_EVENTS_STREAM = "videos:events"

# Event names. Each pipeline step, on completion, emits the next event so a
# downstream consumer (its own group) can pick the work up — see the
# processing slice.
VIDEO_CREATED = "video.created"
VIDEO_DOWNLOADED = "video.downloaded"
VIDEO_TRANSCRIBED = "video.transcribed"
VIDEO_SEGMENTED = "video.segmented"
VIDEO_CUT = "video.cut"
VIDEO_FACE_CROPPED = "video.face_cropped"
VIDEO_SUBTITLED = "video.subtitled"
VIDEO_BURNED = "video.burned"
VIDEO_UPLOADED = "video.uploaded"

# Stream that carries integration lifecycle/command events.
INTEGRATION_EVENTS_STREAM = "integrations:events"

INTEGRATION_SYNC_REQUESTED = "integration.sync_requested"
