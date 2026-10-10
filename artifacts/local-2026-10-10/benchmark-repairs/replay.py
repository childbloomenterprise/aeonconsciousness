"""Two bounded, unchanged-brief repair replays; not a new paired benchmark."""
from pathlib import Path
import runpy
import sys

REPO = Path(__file__).resolve().parents[3]
module = runpy.run_path(str(REPO / 'artifacts/paired-lean-benchmark-2026-10-10/run_framework_arm_r3.py'))
namespace = module['submit'].__globals__
namespace['ROOT'] = Path(__file__).resolve().parent
namespace['CONFIG']['tasks'] = [task for task in namespace['CONFIG']['tasks']
    if task['id'] in {'complex-brief-underfill', 'complex-user-intent-truncated'}]
namespace['KEY_PREFIX'] = 'aeon-20261010-repair-replay-v1-'
namespace['RETRY_SUFFIX'] = {}
if sys.argv[1:] == ['submit']:
    module['submit']()
else:
    module['inspect']()
