# Scenario 4 – energy_b (energy‑only poisoning)
Goal: show an attack that only claims massive battery drain in Sector B (no explicit crash hazard).

Steps:
```
In your shell: export SCENARIO=energy_b
In main.py: keep ENABLE_ATTACK = True
Optionally reset DB for a clean run: rm -f mission_memory.db
Run: python main.py
```

What to expect:
```
Attack phase: only “Injecting Battery Drain in Sector B” (no hazard rule).
Memory after attack: poisoned low‑battery episodes, no hazard rules.
Planning: context shows only energy warnings; depending on how strict you make energy rules later, you can:
For now, likely see Attack Effect: WARN_ONLY (no route change), and later in Phase 6+ adjust behavior so low‑SOC attacks can cause route changes.
```
