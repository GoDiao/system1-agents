"""Verify, without any server, that the clm backend hands CLM exactly what the agent produced.

Builds the same request the tool loop builds for a real ticket -- the environment's observation, the loop's
ChoiceQuestion, the loop's RULES -- sends it through ClmModel with the transport replaced by a recorder, and
compares the recorded body field by field against those inputs.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from s1a.agents.ticket_router import QUEUES, RULES, TicketRouterEnv
from s1a.decision_models import ChoiceQuestion, Observation
from s1a.decision_models.clm import ClmClient, ClmModel


async def main() -> None:
    env = TicketRouterEnv(seed=0, batch_size=1)
    await env.reset()
    observation = await env.observe()
    candidates = await env.candidates()
    offered = {key: text for key, text in candidates.items()}
    question = ChoiceQuestion(offered, rules=RULES)  # exactly what s1a/tool/models.py builds
    print("the agent produced:")
    print(f"  observation = {json.dumps(observation, ensure_ascii=False)}")
    print(f"  candidates  = {json.dumps(candidates, ensure_ascii=False)}")
    print(f"  rules       = {RULES[:60]}... ({len(RULES)} chars)")

    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"models": [{"name": "clm-latest"}]})
        body = json.loads(request.content)
        sent.append(body)
        return httpx.Response(
            200,
            json={
                "model": "clm-latest",
                "answers": {
                    "pick": {
                        "type": "choice",
                        "choice": "human",
                        "confidence": 0.9,
                        "probabilities": {k: 1 / len(offered) for k in offered},
                    }
                },
                "usage": {"input_tokens": 1},
            },
        )

    model = ClmModel(ClmClient(url="http://recorder.test", transport=httpx.MockTransport(handler)))
    await model.decide_many(Observation(observation), {"pick": question})
    await model.close()

    body = sent[0]
    print("\nthe backend sent:")
    print(json.dumps(body, ensure_ascii=False, indent=1)[:900])

    q = body["questions"]["pick"]
    checks = {
        "state is the observation, unchanged": body["state"] == observation,
        "criteria is the candidates, unchanged": q["criteria"] == candidates,
        "every option key survived": set(q["criteria"]) == set(offered),
        "every option description survived": all(q["criteria"][k] == v for k, v in offered.items()),
        "the rules survived in full": RULES in q["instructions"],
        "nothing was added to the criteria": set(q["criteria"]) == set(QUEUES),
    }
    print()
    for name, ok in checks.items():
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    print(f"\nall pass: {all(checks.values())}")


if __name__ == "__main__":
    asyncio.run(main())
