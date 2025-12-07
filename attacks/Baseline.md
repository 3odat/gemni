# Baseline

For Scenario 1 (Baseline), you don’t need new code—just a clean config and run.


Config
```
In main.py:
Set ENABLE_ATTACK = False
```
You can ignore SCENARIO for this case (or leave it as "hazard_a"; it won’t be used when attacks are off).
Run steps
```
From uav_project:
Reset DB once for a clean baseline:
rm -f mission_memory.db
Run baseline:
python main.py
What you should see:
“Attack=OFF” in the header.
Memory snapshot before mission: empty (no poisoned entries, no rules).
Supervisor planning using fallback or model, but with no attack injections.
Both drones take off, move, and scan.
Mission Report: both drones SUCCESS.
```
[Attack Effect] NONE (no hazard influence detected) at the end.
That’s Scenario 1. For the paper, keep this config fixed and later rerun it multiple times as your “baseline” condition against the attack scenarios.
