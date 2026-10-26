-- Reference-only normalized columns: price_cents is an exact integer BRL cent amount.
WITH per_order AS (
    SELECT o.order_id,
           COUNT(i.order_id) AS item_count,
           COUNT(i.price_cents) AS valid_item_count,
           SUM(i.price_cents) AS amount_cents
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    LEFT JOIN order_items i ON i.order_id = o.order_id
    WHERE o.order_purchase_timestamp >= :period_start
      AND o.order_purchase_timestamp < :period_end
      AND c.customer_state = 'SP' AND o.order_status = 'delivered'
    GROUP BY o.order_id
)
SELECT (SELECT COUNT(*) FROM orders o JOIN customers c USING(customer_id)
        WHERE o.order_purchase_timestamp >= :period_start
          AND o.order_purchase_timestamp < :period_end
          AND c.customer_state = 'SP') AS cohort_order_count,
       COUNT(*) AS delivered_order_count,
       COALESCE(SUM(valid_item_count), 0) AS valid_item_count,
       COALESCE(SUM(valid_item_count > 0), 0) AS contributing_order_count,
       COALESCE(SUM(item_count = 0), 0) AS missing_item_order_count,
       COALESCE(SUM(item_count - valid_item_count), 0) AS invalid_item_count,
       CASE WHEN COUNT(*) = 0 THEN 0 ELSE SUM(amount_cents) END AS amount_cents
FROM per_order;
