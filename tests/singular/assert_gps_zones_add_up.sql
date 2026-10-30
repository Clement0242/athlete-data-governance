-- The four speed-zone distances partition the total distance.
select player_id, session_date, distance_m,
       distance_0_2_m + distance_2_43_m + distance_hsr_m + distance_sprint_m as zones_total
from {{ ref('fct_gps_session') }}
where abs(distance_m - (distance_0_2_m + distance_2_43_m + distance_hsr_m + distance_sprint_m)) > 1
