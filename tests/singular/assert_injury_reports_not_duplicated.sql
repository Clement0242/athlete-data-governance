-- The same body location reported twice by a player on the same day.
-- Harmless for episodes (they use distinct reports) but a sign of a double
-- submission in the app.
{{ config(severity = 'warn') }}
select player_id, report_date, body_location, count(*) as n
from {{ ref('stg_soccermon__injury_reports') }}
group by all
having count(*) > 1
