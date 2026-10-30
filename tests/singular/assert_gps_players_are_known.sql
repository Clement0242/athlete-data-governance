-- Orphans: players with GNSS data but no subjective report at all. They
-- cannot be linked to load or injuries, so they are listed, not hidden.
{{ config(severity = 'warn') }}
select player_id, team, n_gps_sessions
from {{ ref('dim_player') }}
where has_objective_data and not has_subjective_data
