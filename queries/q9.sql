select
  nation,
  o_year,
  sum(amount) as sum_profit
from (
  select
    n_name as nation,
    year(o_orderdate) as o_year,
    l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity as amount
  from part
  join lineitem on p_partkey = l_partkey
  join supplier on l_suppkey = s_suppkey
  join partsupp on ps_suppkey = l_suppkey and ps_partkey = l_partkey
  join orders on o_orderkey = l_orderkey
  join nation on s_nationkey = n_nationkey
  where lower(p_name) like '%green%'
) profit
group by nation, o_year
order by nation asc, o_year desc
