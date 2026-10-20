# Adaptive Level 4 Completed Review

## Results

- Mean production score: 1,457, down 42%% from Level 3.
- Mean automated production score: 327, down 43%% from Level 3.
- Production variation decreased by 61%%.
- Automation variation decreased by 60%%.
- The runs produced 286 errors, including 273 placement errors.
- Placement accounted for approximately 95%% of all errors.
- Only 6.6%% of errors were recovered.
- Two runs made no additional production during their final 50 turns.

## What Worked

- All three runs established some production early.
- Existing equipment generated automated output.
- Results became more consistent across the three runs.

## What Did Not Work

- The model became fixated on placing chests and similar entities.
- It repeated placement attempts despite the two-attempt limit.
- It did not reliably verify that the finished entity was in inventory.
- None of the 450 turns used the requested Objective statement.
- Lower variation represented a more consistent failure pattern rather than improved performance.

## Level 5 Decision

The detailed placement rules from Levels 2 through 4 will be superseded by a shorter decision hierarchy. Level 5 will emphasize maintaining productive systems and abandoning unsuccessful objectives. Chest placement will not yet be prohibited. A prohibition will be considered for Level 6 if placement fixation remains present in at least two Level 5 runs.

## Review Status

Completed before the Level 5 adaptive runs.
Source batch: experiment_runs/FLE_adaptive_L04_B20260929T182528
