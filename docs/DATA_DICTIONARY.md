# Run-level data dictionary

`data/final/final_72_run_dataset.csv` contains one row per formal run.

| Column | Meaning |
|---|---|
| `run_id` | Unique arm, level, repeat, and start-time identifier |
| `source_file` | Stable Inspect archive filename |
| `level` | Cumulative instruction level, 1–12 |
| `turns` | Agent turn budget used by the run |
| `production_score` / `production` | Final FLE production score |
| `automated_production_score` / `automated` | Final FLE automated-production score |
| `automation_ratio` | Automated production divided by production |
| `ticks` | Final recorded Factorio tick count |
| `production_per_1000_ticks` | Production score normalized by ticks |
| `automated_per_1000_ticks` | Automated-production score normalized by ticks |
| `errors` | Turns classified as errors |
| `error_rate` | Error turns divided by total turns |
| `recovered_errors` | Errors followed by a successful turn within three turns |
| `recovery_rate` | Recovered errors divided by total errors |
| `longest_error_streak` | Longest consecutive sequence of error turns |
| `longest_repeated_action_streak` / `longest_repeat_streak` | Longest repeated action-signature sequence |
| `productive_turns` | Turns with a production or automation increase |
| `productive_turn_rate` / `productive_rate` | Productive turns divided by total turns |
| `score_auc` | Area under the per-turn production-score curve |
| `automated_score_auc` | Area under the automated-score curve |
| `produced_item_types` | Comma-separated item types observed as produced |
| `researched_technologies` | Comma-separated technologies recorded by FLE |
| `top_error_category` | Most frequent classified error category |
| `selected_arm` | Formal experimental arm (`fixed` or `adaptive`) |
| `selected_level` | Level copied from the selected-batch register |
| `selected_batch_id` | Provenance link to the chosen formal batch |

