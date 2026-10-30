-- The daily load and its derived ratios exactly as the provider computed
-- them. Kept to be *reconciled* against the warehouse's own computation,
-- never used directly by the marts.
with daily as ({{ unpivot_players(source('soccermon', 'daily_load_wide'), 'value') }}),
     atl   as ({{ unpivot_players(source('soccermon', 'atl_wide'), 'value') }}),
     ctl28 as ({{ unpivot_players(source('soccermon', 'ctl28_wide'), 'value') }}),
     acwr  as ({{ unpivot_players(source('soccermon', 'acwr_wide'), 'value') }})

select
    daily.calendar_date,
    daily.player_id,
    daily.team,
    daily.value  as daily_load_au,
    atl.value    as atl_au,
    ctl28.value  as ctl28_au,
    acwr.value   as acwr
from daily
left join atl   using (calendar_date, player_id)
left join ctl28 using (calendar_date, player_id)
left join acwr  using (calendar_date, player_id)
