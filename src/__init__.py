"""DAS732 A3 workflow package: data prep, features, statistics, models and plots."""

import os

# joblib (used by scikit-learn) counts physical CPU cores with `wmic`, which Windows 11 no
# longer ships; the failure prints a warning and a traceback into the notebook. A user
# limit below the logical core count makes joblib skip that lookup. Half the logical cores
# equals the physical cores on hyper-threaded CPUs. Only the number of worker processes
# depends on it, never a result.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(max(1, (os.cpu_count() or 2) // 2)))
