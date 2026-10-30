-- The provider's ACWR must be its ATL divided by its CTL28 (the "coupled"
-- ratio). Checks that the definition in the documentation is the one used.
select *
from {{ ref('stg_soccermon__provider_load_metrics') }}
where ctl28_au > 0
  and abs(acwr - atl_au / ctl28_au) > 0.01
