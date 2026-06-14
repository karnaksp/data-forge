-- Retail source-system validation checks.
-- Run with:
-- docker compose exec -T postgres psql -U admin -d demo < sql/validation/postgres_retail_seed_checks.sql

\echo '1. Seed table row counts'
select 'users' as table_name, count(*) as row_count from users
union all select 'products', count(*) from products
union all select 'warehouses', count(*) from warehouses
union all select 'suppliers', count(*) from suppliers
union all select 'inventory', count(*) from inventory
union all select 'warehouse_inventory', count(*) from warehouse_inventory
union all select 'customer_segments', count(*) from customer_segments
union all select 'product_suppliers', count(*) from product_suppliers
order by table_name;

\echo '2. Duplicate key checks'
select 'users.user_id' as key_name, count(*) - count(distinct user_id) as duplicate_count from users
union all select 'products.product_id', count(*) - count(distinct product_id) from products
union all select 'warehouses.warehouse_id', count(*) - count(distinct warehouse_id) from warehouses
union all select 'suppliers.supplier_id', count(*) - count(distinct supplier_id) from suppliers;

\echo '3. Referential integrity checks'
select 'inventory.product_id missing in products' as check_name, count(*) as issue_count
from inventory i
left join products p on p.product_id = i.product_id
where p.product_id is null
union all
select 'warehouse_inventory.product_id missing in products', count(*)
from warehouse_inventory wi
left join products p on p.product_id = wi.product_id
where p.product_id is null
union all
select 'warehouse_inventory.warehouse_id missing in warehouses', count(*)
from warehouse_inventory wi
left join warehouses w on w.warehouse_id = wi.warehouse_id
where w.warehouse_id is null
union all
select 'customer_segments.user_id missing in users', count(*)
from customer_segments cs
left join users u on u.user_id = cs.user_id
where u.user_id is null
union all
select 'product_suppliers.product_id missing in products', count(*)
from product_suppliers ps
left join products p on p.product_id = ps.product_id
where p.product_id is null
union all
select 'product_suppliers.supplier_id missing in suppliers', count(*)
from product_suppliers ps
left join suppliers s on s.supplier_id = ps.supplier_id
where s.supplier_id is null;

\echo '4. Inventory sanity checks'
select
    count(*) filter (where qty < 0) as negative_global_qty,
    count(*) filter (where price_usd <= 0) as non_positive_product_prices
from inventory i
join products p on p.product_id = i.product_id;

select
    count(*) filter (where qty < 0) as negative_warehouse_qty,
    count(*) filter (where reserved_qty < 0) as negative_reserved_qty,
    count(*) filter (where reserved_qty > qty) as reserved_above_qty
from warehouse_inventory;

\echo '5. Retail profile'
select
    p.category,
    count(*) as product_count,
    round(avg(p.price_usd)::numeric, 2) as avg_price_usd,
    sum(i.qty) as global_inventory_qty
from products p
join inventory i on i.product_id = p.product_id
group by p.category
order by global_inventory_qty desc;
