-- Reported training sessions (deduplicated). Grain: one session.
select
    session_id,
    player_id,
    team,
    session_date,
    rpe,
    duration_min,
    srpe_au,
    rpe = 0 or duration_min = 0 as is_incomplete_report
from {{ ref('int_training_sessions__deduplicated') }}
