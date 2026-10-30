-- Quarantine, not deletion: every recording keeps its row and gets two flags.
--
-- gps_quality_flag   ok | duplicate_file_name | implausible_duration | implausible_distance | gnss_speed_spike
--   Two different recordings under the same file name (TeamB 2021): nothing
--   says which one is the player's, so neither is used.
--   A unit left recording all day (> 5 h, > 16 km) or a GNSS jump above
--   10 m/s (faster than any elite woman sprints) makes the session unusable.
-- hr_quality_flag    ok | no_heart_rate | frozen_sensor
--   The strap was optional: many sessions have no heart rate. Some report a
--   constant 82 bpm for the whole session, the strap's default value: a
--   frozen sensor, which would otherwise pass every range check.
with s as (
    select
        *,
        list_sum(hr_seconds_by_bpm)                                         as hr_seconds,
        list_max(hr_seconds_by_bpm) / nullif(list_sum(hr_seconds_by_bpm), 0) as hr_mode_share
    from {{ ref('stg_objective__gps_sessions') }}
)

select
    *,
    case
        when count(*) over (partition by source_file) > 1 then 'duplicate_file_name'
        when duration_min > 300                  then 'implausible_duration'
        when distance_m > 16000                  then 'implausible_distance'
        when speed_max_ms > 10                   then 'gnss_speed_spike'
        else 'ok'
    end as gps_quality_flag,
    case
        when hr_seconds < 600 or hr_coverage < 0.5 then 'no_heart_rate'
        when hr_mode_share > 0.5                   then 'frozen_sensor'
        else 'ok'
    end as hr_quality_flag
from s
