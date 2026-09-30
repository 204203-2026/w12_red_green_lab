"""Root conftest injected into a throwaway variant workspace by the grader.

The variants are NOT shipped implementations — there is no reference copy of
`/api/stats` anywhere in this template, on purpose. A student who received one
could paste it into app/main.py and never write a test, which is the exact
habit this lab exists to build.

Instead each variant is derived at check time from the student's OWN app by
perturbing the JSON that /api/stats returns. That keeps the oracle honest
(their tests must still tell a correct response from a broken one) while the
answer never leaves the grader.

Selected by the W12_VARIANT environment variable.
"""

import json
import os

from starlette.responses import JSONResponse

from app import main

VARIANT = os.environ.get("W12_VARIANT", "reference")


def perturb(payload):
    """Return the broken version of a correct /api/stats body."""
    if not isinstance(payload, dict):
        return payload
    broken = dict(payload)
    total = payload.get("total")
    done = payload.get("done")

    if VARIANT == "mutant_a":                       # off by one
        if isinstance(done, (int, float)):
            broken["done"] = done + 1
    elif VARIANT == "mutant_b":                     # ratio, not percent
        if isinstance(done, (int, float)) and isinstance(total, (int, float)) and total:
            broken["percent_done"] = done / total
    elif VARIANT == "mutant_c":                     # total off by one
        if isinstance(total, (int, float)):
            broken["total"] = total + 1
    elif VARIANT == "mutant_d":                     # always complete
        broken["percent_done"] = 100.0
    return broken


if VARIANT != "reference":

    @main.app.middleware("http")
    async def _apply_variant(request, call_next):
        if request.url.path != "/api/stats":
            return await call_next(request)

        if VARIANT == "stub":
            return JSONResponse(
                {"detail": "Write tests first; feature missing"}, status_code=501
            )

        response = await call_next(request)
        if response.status_code != 200:
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        try:
            payload = json.loads(body)
        except ValueError:
            return JSONResponse(content=None, status_code=response.status_code)
        return JSONResponse(perturb(payload), status_code=200)
