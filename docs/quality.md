# Data quality report

Generated from the last `dbt build`: **108 rules, 103 passed, 5 warnings, 0 failures.**

| Mart | Rows |
|---|---:|
| `dim_player` | 78 |
| `fct_training_session` | 16,189 |
| `fct_gps_session` | 10,075 |
| `fct_injury_episode` | 101 |
| `fct_player_day` | 30,573 |

## Warnings: what the rules found in the source

### `assert_injury_reports_not_duplicated` — 6 rows

Source defect, harmless. The same body location reported twice on the same day (double submission). Episodes are built from distinct reports, so they are not affected.

### `assert_gps_file_names_unique` — 81 rows

Source defect, quarantined. The 2021 archive of one team holds two *different* recordings under the same file name for 2 players (distance and duration differ). Nothing says which one is the player's, so both are flagged duplicate_file_name and neither feeds an indicator.

### `assert_gps_player_from_file_name` — 3 rows

Source defect, repaired. GNSS files whose player column is empty although the file name carries the player identifier. The identifier is recovered from the file name, a rule that is visible in staging, and the files are listed here.

### `assert_provider_daily_load_reconciles` — 110 rows

Source defect. For 3 players the provider's daily load is higher than the sum of the exported session reports (never lower): sessions are missing from `session.json`. The warehouse recomputes the load from the sessions it has and never uses the provider's figure.

### `assert_gps_players_are_known` — 28 rows

Source defect. Players with GNSS recordings but no questionnaire at all. Their identifiers use another UUID format than PmSys's, and about as many players have questionnaires but no GNSS: most likely the same players pseudonymised twice. A record linkage on attendance (GNSS days vs RPE days) was tried and cannot tell them apart, because teammates train on the same days. No link is guessed: the mapping has to come from the provider. Until then their GNSS data stays in fct_gps_session but cannot be related to load, wellness or injuries.

## Quarantined recordings

Recordings are never deleted: each one is flagged, and indicators are computed on valid data only.

| GNSS | Heart rate | Recordings |
|---|---|---:|
| ok | no_heart_rate | 5,753 |
| ok | frozen_sensor | 2,728 |
| ok | ok | 1,323 |
| duplicate_file_name | frozen_sensor | 91 |
| duplicate_file_name | no_heart_rate | 71 |
| gnss_speed_spike | frozen_sensor | 35 |
| gnss_speed_spike | no_heart_rate | 25 |
| implausible_duration | no_heart_rate | 17 |
| implausible_distance | no_heart_rate | 9 |
| implausible_duration | frozen_sensor | 9 |
| implausible_distance | frozen_sensor | 8 |
| gnss_speed_spike | ok | 3 |
| implausible_distance | ok | 3 |

`frozen_sensor`: a constant 82 bpm for most of the session, the strap's default value. It would pass every range check; it is caught by the share of time spent at a single value.

## All rules

| Result | Rule | Model | Column | Failing rows |
|---|---|---|---|---:|
| warn | `assert_gps_file_names_unique` | `several` |  | 81 |
| warn | `assert_gps_player_from_file_name` | `several` |  | 3 |
| warn | `assert_gps_players_are_known` | `several` |  | 28 |
| warn | `assert_injury_reports_not_duplicated` | `several` |  | 6 |
| warn | `assert_provider_daily_load_reconciles` | `several` |  | 110 |
| pass | `not_null` | `body_locations` | body_location | 0 |
| pass | `unique` | `body_locations` | body_location | 0 |
| pass | `accepted_range` | `dim_player` | n_days | 0 |
| pass | `accepted_range` | `dim_player` | hr_max_estimated_bpm | 0 |
| pass | `accepted_range` | `dim_player` | wellness_coverage | 0 |
| pass | `accepted_values` | `dim_player` | team | 0 |
| pass | `not_null` | `dim_player` | first_day | 0 |
| pass | `not_null` | `dim_player` | last_day | 0 |
| pass | `not_null` | `dim_player` | n_days | 0 |
| pass | `not_null` | `dim_player` | player_id | 0 |
| pass | `not_null` | `dim_player` | team | 0 |
| pass | `unique` | `dim_player` | player_id | 0 |
| pass | `accepted_range` | `fct_gps_session` | distance_m | 0 |
| pass | `accepted_range` | `fct_gps_session` | duration_min | 0 |
| pass | `accepted_range` | `fct_gps_session` | hr_coverage | 0 |
| pass | `accepted_range` | `fct_gps_session` | hr_mean_bpm | 0 |
| pass | `accepted_range` | `fct_gps_session` | hr_peak_bpm | 0 |
| pass | `accepted_range` | `fct_gps_session` | speed_max_ms | 0 |
| pass | `accepted_values` | `fct_gps_session` | gps_quality_flag | 0 |
| pass | `accepted_values` | `fct_gps_session` | hr_quality_flag | 0 |
| pass | `accepted_values` | `fct_gps_session` | team | 0 |
| pass | `not_null` | `fct_gps_session` | distance_m | 0 |
| pass | `not_null` | `fct_gps_session` | duration_min | 0 |
| pass | `not_null` | `fct_gps_session` | gps_quality_flag | 0 |
| pass | `not_null` | `fct_gps_session` | hr_quality_flag | 0 |
| pass | `not_null` | `fct_gps_session` | player_id | 0 |
| pass | `not_null` | `fct_gps_session` | recording_id | 0 |
| pass | `not_null` | `fct_gps_session` | session_date | 0 |
| pass | `not_null` | `fct_gps_session` | source_file | 0 |
| pass | `not_null` | `fct_gps_session` | team | 0 |
| pass | `relationships` | `fct_gps_session` | player_id | 0 |
| pass | `unique` | `fct_gps_session` | recording_id | 0 |
| pass | `unique_combination_of_columns` | `fct_gps_session` |  | 0 |
| pass | `accepted_range` | `fct_injury_episode` | span_days | 0 |
| pass | `accepted_values` | `fct_injury_episode` | team | 0 |
| pass | `accepted_values` | `fct_injury_episode` | worst_severity | 0 |
| pass | `expression_is_true` | `fct_injury_episode` |  | 0 |
| pass | `not_null` | `fct_injury_episode` | body_location | 0 |
| pass | `not_null` | `fct_injury_episode` | injury_episode_id | 0 |
| pass | `not_null` | `fct_injury_episode` | last_report_date | 0 |
| pass | `not_null` | `fct_injury_episode` | onset_date | 0 |
| pass | `not_null` | `fct_injury_episode` | player_id | 0 |
| pass | `not_null` | `fct_injury_episode` | team | 0 |
| pass | `not_null` | `fct_injury_episode` | worst_severity | 0 |
| pass | `relationships` | `fct_injury_episode` | body_location | 0 |
| pass | `relationships` | `fct_injury_episode` | player_id | 0 |
| pass | `unique` | `fct_injury_episode` | injury_episode_id | 0 |
| pass | `accepted_range` | `fct_player_day` | readiness | 0 |
| pass | `accepted_range` | `fct_player_day` | sleep_duration | 0 |
| pass | `accepted_range` | `fct_player_day` | fatigue | 0 |
| pass | `accepted_range` | `fct_player_day` | mood | 0 |
| pass | `accepted_range` | `fct_player_day` | sleep_quality | 0 |
| pass | `accepted_range` | `fct_player_day` | soreness | 0 |
| pass | `accepted_range` | `fct_player_day` | stress | 0 |
| pass | `accepted_values` | `fct_player_day` | team | 0 |
| pass | `not_null` | `fct_player_day` | calendar_date | 0 |
| pass | `not_null` | `fct_player_day` | has_rpe | 0 |
| pass | `not_null` | `fct_player_day` | has_wellness | 0 |
| pass | `not_null` | `fct_player_day` | has_gps | 0 |
| pass | `not_null` | `fct_player_day` | is_injured | 0 |
| pass | `not_null` | `fct_player_day` | is_ill | 0 |
| pass | `not_null` | `fct_player_day` | n_rpe_sessions | 0 |
| pass | `not_null` | `fct_player_day` | is_injury_onset | 0 |
| pass | `not_null` | `fct_player_day` | player_id | 0 |
| pass | `not_null` | `fct_player_day` | team | 0 |
| pass | `relationships` | `fct_player_day` | player_id | 0 |
| pass | `unique_combination_of_columns` | `fct_player_day` |  | 0 |
| pass | `accepted_range` | `fct_training_session` | rpe | 0 |
| pass | `accepted_range` | `fct_training_session` | duration_min | 0 |
| pass | `accepted_range` | `fct_training_session` | srpe_au | 0 |
| pass | `accepted_values` | `fct_training_session` | team | 0 |
| pass | `expression_is_true` | `fct_training_session` |  | 0 |
| pass | `not_null` | `fct_training_session` | duration_min | 0 |
| pass | `not_null` | `fct_training_session` | player_id | 0 |
| pass | `not_null` | `fct_training_session` | rpe | 0 |
| pass | `not_null` | `fct_training_session` | session_date | 0 |
| pass | `not_null` | `fct_training_session` | session_id | 0 |
| pass | `not_null` | `fct_training_session` | srpe_au | 0 |
| pass | `not_null` | `fct_training_session` | team | 0 |
| pass | `relationships` | `fct_training_session` | player_id | 0 |
| pass | `unique` | `fct_training_session` | session_id | 0 |
| pass | `accepted_range` | `mart_source_coverage` | rpe_coverage | 0 |
| pass | `accepted_range` | `mart_source_coverage` | gps_coverage | 0 |
| pass | `accepted_range` | `mart_source_coverage` | wellness_coverage | 0 |
| pass | `accepted_values` | `mart_source_coverage` | team | 0 |
| pass | `not_null` | `mart_source_coverage` | month | 0 |
| pass | `not_null` | `mart_source_coverage` | n_days | 0 |
| pass | `not_null` | `mart_source_coverage` | player_id | 0 |
| pass | `not_null` | `mart_source_coverage` | team | 0 |
| pass | `relationships` | `mart_source_coverage` | player_id | 0 |
| pass | `unique_combination_of_columns` | `mart_source_coverage` |  | 0 |
| pass | `assert_gps_zones_add_up` | `several` |  | 0 |
| pass | `assert_provider_acwr_is_atl_over_ctl28` | `several` |  | 0 |
| pass | `not_null` | `stg_objective__gps_sessions` | recording_id | 0 |
| pass | `unique` | `stg_objective__gps_sessions` | recording_id | 0 |
| pass | `accepted_values` | `stg_soccermon__injury_reports` | severity | 0 |
| pass | `relationships` | `stg_soccermon__injury_reports` | body_location | 0 |
| pass | `accepted_range` | `stg_soccermon__training_sessions` | rpe | 0 |
| pass | `expression_is_true` | `stg_soccermon__training_sessions` |  | 0 |
| pass | `not_null` | `stg_soccermon__training_sessions` | session_id | 0 |
| pass | `row_count_between` | `stg_soccermon__training_sessions` |  | 0 |
| pass | `unique` | `stg_soccermon__training_sessions` | session_id | 0 |
| pass | `unique_combination_of_columns` | `stg_soccermon__wellness` |  | 0 |
