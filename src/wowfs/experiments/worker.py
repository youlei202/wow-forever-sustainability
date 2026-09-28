"""Execute an isolated frozen-source instance; stdout is machine-readable JSON."""
import json
import sys
from pathlib import Path
from wowfs.experiments.exact import run_instance
from wowfs.paths import atomic_json

if __name__ == "__main__":
    seed, variant, horizon = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    def checkpoint(state):
        atomic_json(Path.cwd() / "round_checkpoints" / f"{variant}-{seed}-round-{state['completed_round']}.json", state)
    result = run_instance(seed=seed, variant=variant, horizon=horizon, checkpoint_callback=checkpoint)
    print(json.dumps(result, allow_nan=False))
