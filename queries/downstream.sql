-- downstream data
WITH
cte AS ( 
  SELECT ed.event_id AS event_id,
         cmf_sp.customer_name AS service_provider_customer_name,
         cmf_sp.customer_id AS service_provider_customer_name_id,
         cmf_cc.customer_name AS forwarded_1,
         cmf_cc.customer_id AS forwarded_1_id,
         ed.created_at
  FROM event_dispatches ed
  LEFT JOIN service_centers cc ON cc.id = ed.call_center_id
  LEFT JOIN tenants t_cc ON cc.tenant_id = t_cc.id
  LEFT JOIN customer_mdm.customer_tenant_mapping ctmf_cc ON ctmf_cc.tenant_id = t_cc.id
  LEFT JOIN customer_mdm.customer_master cmf_cc ON cmf_cc.customer_id = ctmf_cc.customer_id
  LEFT JOIN events e ON e.id = ed.event_id
  LEFT JOIN service_centers sp ON sp.id = ed.service_provider_id
  LEFT JOIN tenants t_sp ON sp.tenant_id = t_sp.id
  LEFT JOIN customer_mdm.customer_tenant_mapping ctmf_sp ON ctmf_sp.tenant_id = t_sp.id
  LEFT JOIN customer_mdm.customer_master cmf_sp ON cmf_sp.customer_id = ctmf_sp.customer_id
  WHERE t_cc.test_tenant = 'false' 
    AND t_sp.test_tenant = 'false' 
    AND e.type = 'Incident' 
    AND e.created_at >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE, -{period}))

    AND e.created_at < DATE_TRUNC('month', CURRENT_DATE) 
    AND e.status NOT IN (3,10,16,18)
)
, ranked_data AS (
  SELECT
    event_id,
    service_provider_customer_name,
    service_provider_customer_name_id,
    forwarded_1,
    forwarded_1_id,
    ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY created_at ASC) AS forward_order
  FROM cte
)
, forwarded AS  ( 
  SELECT
    event_id,
    MAX(CASE WHEN forward_order = 1 THEN forwarded_1 END) AS forwarded_1,
    MAX(CASE WHEN forward_order = 1 THEN forwarded_1_id END) AS forwarded_1_id,
    MAX(CASE WHEN forward_order = 1 THEN service_provider_customer_name END) AS forwarded_2,
    MAX(CASE WHEN forward_order = 1 THEN service_provider_customer_name_id END) AS forwarded_2_id,
    MAX(CASE WHEN forward_order = 2 THEN service_provider_customer_name END) AS forwarded_3,
    MAX(CASE WHEN forward_order = 2 THEN service_provider_customer_name_id END) AS forwarded_3_id,
    MAX(CASE WHEN forward_order = 3 THEN service_provider_customer_name END) AS forwarded_4,
    MAX(CASE WHEN forward_order = 3 THEN service_provider_customer_name_id END) AS forwarded_4_id,
    MAX(CASE WHEN forward_order = 4 THEN service_provider_customer_name END) AS forwarded_5,
    MAX(CASE WHEN forward_order = 4 THEN service_provider_customer_name_id END) AS forwarded_5_id,
    MAX(CASE WHEN forward_order = 5 THEN service_provider_customer_name END) AS forwarded_6,
    MAX(CASE WHEN forward_order = 5 THEN service_provider_customer_name_id END) AS forwarded_6_id
  FROM ranked_data rd
  GROUP BY event_id
)
, dispatch_table_cte AS ( 
  SELECT rd.event_id, cmf.customer_name AS fleet, cmf.customer_id AS fleet_id,
         rd.forwarded_1, rd.forwarded_1_id, rd.forwarded_2, rd.forwarded_2_id, 
         rd.forwarded_3, rd.forwarded_3_id, rd.forwarded_4, rd.forwarded_4_id, 
         rd.forwarded_5, rd.forwarded_5_id, rd.forwarded_6, rd.forwarded_6_id    
  FROM forwarded rd
  LEFT JOIN events e ON e.id = rd.event_id
  LEFT JOIN truck_dispatches td ON td.id = e.truck_dispatch_id
  LEFT JOIN tenants t ON t.id = td.tenant_id
  LEFT JOIN customer_mdm.customer_tenant_mapping ctmf ON ctmf.tenant_id = t.id
  LEFT JOIN customer_mdm.customer_master cmf ON cmf.customer_id = ctmf.customer_id 
)
, events_table_cte AS ( 
  SELECT 
    e.id AS event_id, 
    cmf.customer_name AS fleet, 
    cmf.customer_id AS fleet_id,
    cmf_sp.customer_name AS forwarded_1,
    cmf_sp.customer_id AS forwarded_1_id,
    NULL AS forwarded_2,
    NULL AS forwarded_2_id,
    NULL AS forwarded_3,
    NULL AS forwarded_3_id,
    NULL AS forwarded_4,
    NULL AS forwarded_4_id, 
    NULL AS forwarded_5,
    NULL AS forwarded_5_id,
    NULL AS forwarded_6,
    NULL AS forwarded_6_id
  FROM events e
  LEFT JOIN truck_dispatches td ON td.id = e.truck_dispatch_id
  LEFT JOIN tenants t ON t.id = td.tenant_id
  LEFT JOIN customer_mdm.customer_tenant_mapping ctmf ON ctmf.tenant_id = t.id
  LEFT JOIN customer_mdm.customer_master cmf ON cmf.customer_id = ctmf.customer_id
  LEFT JOIN service_centers sp ON sp.id = e.service_center_id
  LEFT JOIN tenants t_sp ON sp.tenant_id = t_sp.id
  LEFT JOIN customer_mdm.customer_tenant_mapping ctmf_sp ON ctmf_sp.tenant_id = t_sp.id
  LEFT JOIN customer_mdm.customer_master cmf_sp ON cmf_sp.customer_id = ctmf_sp.customer_id
  WHERE 
    t.test_tenant = 'false' 
    AND t_sp.test_tenant = 'false'
    AND e.type = 'Incident' 
    AND e.created_at >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE, -{period}))

    AND e.created_at < DATE_TRUNC('month', CURRENT_DATE) 
    AND e.status NOT IN (3,10,16,18)
    And e.id not in (select event_id from dispatch_table_cte)
)
, union_table as (
  SELECT * FROM events_table_cte
  UNION ALL
  SELECT * FROM dispatch_table_cte 
)
,

flattened AS (
    SELECT event_id, fleet, fleet_id, forwarded_1, forwarded_1_id,  1 AS unnest_position FROM union_table
  UNION ALL
    SELECT event_id, forwarded_1, forwarded_1_id, forwarded_2, forwarded_2_id,  2 AS unnest_position FROM union_table
  UNION ALL
    SELECT event_id, forwarded_2, forwarded_2_id, forwarded_3, forwarded_3_id,  3 AS unnest_position FROM union_table
  UNION ALL
    SELECT event_id, forwarded_3, forwarded_3_id, forwarded_4, forwarded_4_id,  4 AS unnest_position FROM union_table
  UNION ALL
    SELECT event_id, forwarded_4, forwarded_4_id, forwarded_5, forwarded_5_id,  5 AS unnest_position FROM union_table
  UNION ALL
    SELECT event_id, forwarded_5, forwarded_5_id, forwarded_6, forwarded_6_id,  6 AS unnest_position FROM union_table
)
, flattened_2 as ( select * from flattened where fleet_id <> forwarded_1_id and forwarded_1_id is not null)

, flattened_rank as ( select *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY unnest_position ASC) AS forward_order from flattened_2 ) 

, dist_event_id as (select distinct event_id as dist_event_id from flattened_rank)

, remove_dublicates AS (
select dist_event_id as event_id , 
max (case when forward_order = 1 then fleet end ) as fleet , 
max (case when forward_order = 1 then fleet_id end) as fleet_id ,
max (case when forward_order = 1 then forwarded_1 end) as forwarded_1,
max (case when forward_order = 1 then forwarded_1_id end )as forwarded_1_id,

max (case when forward_order = 2 then forwarded_1 end )as forwarded_2,
max (case when forward_order = 2 then forwarded_1_id end) as forwarded_2_id,

max (case when forward_order = 3 then forwarded_1 end )as forwarded_3,
max (case when forward_order = 3 then forwarded_1_id end) as forwarded_3_id,

max (case when forward_order = 4 then forwarded_1 end) as forwarded_4,
max (case when forward_order = 4 then forwarded_1_id end) as forwarded_4_id,

max (case when forward_order = 5 then forwarded_1 end )as forwarded_5,
max (case when forward_order = 5 then forwarded_1_id end )as forwarded_5_id,

max (case when forward_order = 6 then forwarded_1 end )as forwarded_6,
max (case when forward_order = 6 then forwarded_1_id end )as forwarded_6_id

from dist_event_id de left join flattened_rank rnk on de.dist_event_id= rnk.event_id 
group by dist_event_id)

, agree as (
select 
COUNT(DISTINCT event_id) as event_count, fleet as customer, fleet_id as customer_id, forwarded_1 as customer_1, forwarded_1_id as customer_1_id, forwarded_2 as customer_2, forwarded_2_id as customer_2_id, forwarded_3 as customer_3, forwarded_3_id as customer_3_id, forwarded_4 as customer_4, forwarded_4_id as customer_4_id, forwarded_5 as customer_5, forwarded_5_id as customer_5_id, forwarded_6 as customer_6, forwarded_6_id as customer_6_id
from remove_dublicates 
where fleet is not null
group by fleet, fleet_id, forwarded_1, forwarded_1_id, forwarded_2, forwarded_2_id, forwarded_3, forwarded_3_id, forwarded_4, forwarded_4_id, forwarded_5, forwarded_5_id, forwarded_6, forwarded_6_id
)
, union_all as (
SELECT event_count,	customer,	customer_id	,customer_1	,customer_1_id,	customer_2,	customer_2_id	,customer_3	,customer_3_id	,customer_4	,customer_4_id	,customer_5	,customer_5_id	,customer_6,	customer_6_id		from agree 
UNION ALL
select event_count, customer_1  as customer,  customer_1_id	as customer_id, customer_2	as customer_1,	customer_2_id	as customer_1_id,	customer_3	as customer_3,	customer_3_id	as customer_3_id,	customer_4	as customer_3,	customer_4_id	as customer_3_id,	customer_5	as customer_4,	customer_5_id	as customer_4_id,	customer_6	as customer_5,	customer_6_id	as customer_5_id,	null 	as customer_6,	null 	as customer_6_id	from agree 
UNION ALL
select event_count,	customer_2	as customer,	customer_2_id	as customer_id,	customer_3	as customer_1,	customer_3_id	as customer_1_id,	customer_4	as customer_3,	customer_4_id	as customer_3_id,	customer_5	as customer_3,	customer_5_id	as customer_3_id,	customer_6	as customer_4,	customer_6_id	as customer_4_id,	null 	as customer_5,	null 	as customer_5_id,	null 	as customer_6,	null 	as customer_6_id	from agree 
UNION ALL
select event_count,	customer_3	as customer,	customer_3_id	as customer_id,	customer_4	as customer_1,	customer_4_id	as customer_1_id,	customer_5	as customer_3,	customer_5_id	as customer_3_id,	customer_6	as customer_3,	customer_6_id	as customer_3_id,	null 	as customer_4,	null 	as customer_4_id,	null 	as customer_5,	null 	as customer_5_id,	null 	as customer_6,	null 	as customer_6_id	from agree 
UNION ALL
select event_count,	customer_4	as customer,	customer_4_id	as customer_id,	customer_5	as customer_1,	customer_5_id	as customer_1_id,	customer_6	as customer_3,	customer_6_id	as customer_3_id,	null	as customer_3	, null 	as customer_3_id,	null 	as customer_4,	null 	as customer_4_id,	null 	as customer_5,	null 	as customer_5_id,	null 	as customer_6,	null 	as customer_6_id	from agree 
UNION ALL
select event_count,	customer_5	as customer,	customer_5_id	as customer_id,	customer_6	as customer_1,	customer_6_id	as customer_1_id,	null 	as customer_3,	null	as customer_3_id,	null	as customer_3,	null 	as customer_3_id,	null 	as customer_4,	null 	as customer_4_id,	null 	as customer_5,	null 	as customer_5_id,	null 	as customer_6,	null 	as customer_6_id	from agree
)
select * from union_all where customer is not null and customer_1 is not null