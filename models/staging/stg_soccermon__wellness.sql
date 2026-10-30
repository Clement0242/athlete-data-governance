-- Daily wellness questionnaire in long format: one row per player, day and
-- item actually answered (unanswered items are absent, not zero).
select calendar_date, player_id, team, 'readiness' as item, value
from ({{ unpivot_players(source('soccermon', 'wellness_readiness_wide'), 'value') }})

union all

select calendar_date, player_id, team, 'fatigue' as item, value
from ({{ unpivot_players(source('soccermon', 'wellness_fatigue_wide'), 'value') }})

union all

select calendar_date, player_id, team, 'soreness' as item, value
from ({{ unpivot_players(source('soccermon', 'wellness_soreness_wide'), 'value') }})

union all

select calendar_date, player_id, team, 'stress' as item, value
from ({{ unpivot_players(source('soccermon', 'wellness_stress_wide'), 'value') }})

union all

select calendar_date, player_id, team, 'mood' as item, value
from ({{ unpivot_players(source('soccermon', 'wellness_mood_wide'), 'value') }})

union all

select calendar_date, player_id, team, 'sleep_quality' as item, value
from ({{ unpivot_players(source('soccermon', 'wellness_sleep_quality_wide'), 'value') }})

union all

select calendar_date, player_id, team, 'sleep_duration' as item, value
from ({{ unpivot_players(source('soccermon', 'wellness_sleep_duration_wide'), 'value') }})
