This task is **already shipped**. The `groupTasksIntoWaves()` function exists at `scripts/regen-task.mjs:252–288`, is exported, and has 11 tests covering all the edge cases specified in the architecture (independent tasks, linear chains, diamonds, cycles, empty input, external deps, real-world epic graphs).

The implementation matches the architecture spec exactly:
- **Kahn's algorithm** with iterative wave extraction
- **Cycle detection** throws with task numbers
- **External dep filtering** (deps not in the input set are ignored)
- Returns `Array<Array<Task>>` where each inner array is one wave

This was likely shipped as part of one of the prior commits (the git log shows batch commits for parallel generation features). Generating an implementation guide for already-completed work would be counterproductive.

Is there a different task you'd like me to generate a guide for, or did you want me to verify/audit the existing implementation against the architecture spec?