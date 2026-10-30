-- Reconciliation: the provider's daily load must equal the sum of the
-- session reports it was computed from. Rows returned are disagreements.
-- Severity warn: it documents a known defect of the source (docs/quality.md).
{{ config(severity = 'warn') }}
with computed as (
    select player_id, session_date as calendar_date, sum(srpe_au) as srpe_from_sessions
    from {{ ref('stg_soccermon__training_sessions') }}
    group by all
)
select p.player_id, p.calendar_date, p.daily_load_au, coalesce(c.srpe_from_sessions, 0) as srpe_from_sessions
from {{ ref('stg_soccermon__provider_load_metrics') }} p
left join computed c using (player_id, calendar_date)
where abs(p.daily_load_au - coalesce(c.srpe_from_sessions, 0)) > 0.5
