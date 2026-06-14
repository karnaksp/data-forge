-- Source-system retail profile.
-- Engine: Postgres.

select
    u.country,
    cs.segment,
    count(*) as customers,
    round(avg(cs.lifetime_value)::numeric, 2) as avg_lifetime_value
from users u
join customer_segments cs on cs.user_id = u.user_id
group by u.country, cs.segment
order by customers desc, u.country, cs.segment;

with product_metrics as (
    select
        category,
        count(*) as products,
        round(avg(price_usd)::numeric, 2) as avg_price_usd
    from products
    group by category
),
supplier_metrics as (
    select
        p.category,
        count(distinct ps.supplier_id) as suppliers,
        round(avg(ps.cost_usd)::numeric, 2) as avg_supplier_cost_usd,
        round(avg(ps.lead_time_days)::numeric, 1) as avg_lead_time_days
    from products p
    left join product_suppliers ps on ps.product_id = p.product_id
    group by p.category
)
select
    pm.category,
    pm.products,
    sm.suppliers,
    pm.avg_price_usd,
    sm.avg_supplier_cost_usd,
    sm.avg_lead_time_days
from product_metrics pm
join supplier_metrics sm using (category)
order by pm.products desc;

select
    w.region,
    w.country,
    count(distinct wi.warehouse_id) as warehouses,
    count(distinct wi.product_id) as stocked_products,
    sum(wi.qty) as available_qty,
    sum(wi.reserved_qty) as reserved_qty,
    round(sum(wi.reserved_qty)::numeric / nullif(sum(wi.qty), 0), 4) as reserved_ratio
from warehouse_inventory wi
join warehouses w on w.warehouse_id = wi.warehouse_id
group by w.region, w.country
order by available_qty desc;
