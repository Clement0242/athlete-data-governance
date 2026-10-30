-- Sessions used by every load computation: exact repeats removed.
-- The choice is documented (docs/quality.md): two sessions of the same
-- player, same day, same RPE and same duration are far more likely a double
-- submission in the app than two identical sessions.
select * exclude (is_exact_repeat)
from {{ ref('stg_soccermon__training_sessions') }}
where not is_exact_repeat
