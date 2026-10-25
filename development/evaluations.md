# Behavioral evaluation

Each `evals/evals.json` retains fixed prompts, expected outcomes and expectations.
Resolve its `files` relative to the eval directory. Use the same evidence and prompt
in fresh baseline/candidate contexts, retain actual tool traces and generated
answers, and grade the expectations against those outputs. Native skill-creator
can orchestrate grading and review; record the actual provider/tool limitations.

Store run outputs under the skill's ignored `evals/runs/` or repository `reports/`.
Never turn canned prose, unconditional passes or echoed dietary/profile flags into
claims of agent behavior. Recipe dietary suitability needs actual ingredient review;
route geometry and itinerary prose need actual generated itineraries.

The three historical deterministic graders were retired. Their useful unique CLI,
localization, offline parsing and lodging checks are retained in regression tests.
Run `make test-skills` for those executable contracts. It does not certify native
advisory quality, live provider access or recipe safety.
