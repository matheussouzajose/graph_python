"""Import-side-effect module that registers every ORM model on Base.metadata.

The FastAPI app registers models transitively (routers import the slices),
and Alembic lists them in `migrations/env.py`. Standalone processes
(workers) import neither, so a cross-table foreign key (e.g. videos.user_id
-> users) can't be resolved at flush time unless every referenced table is
registered. Importing this module once makes the metadata complete.

Keep this list in sync with `migrations/env.py`.
"""

import app.core.infrastructure.messaging.outbox.orm  # noqa: F401
import app.features.company.orm  # noqa: F401
import app.features.integration.orm  # noqa: F401
