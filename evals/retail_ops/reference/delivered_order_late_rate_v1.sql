-- Input: orders/customers from the fixed Olist snapshot.
-- The runner parses timestamps strictly and loads invalid/empty values as NULL.
-- :period_start and :period_end: normalized YYYY-MM-DD HH:MM:SS.
-- :customer_state: NULL = all states; otherwise one exact state code.
WITH cohort AS (
    SELECT o.*,
           COALESCE(NULLIF(c.customer_state, ''), 'UNKNOWN') AS customer_state
    FROM orders AS o
    LEFT JOIN customers AS c ON c.customer_id = o.customer_id
    WHERE o.order_purchase_timestamp >= :period_start
      AND o.order_purchase_timestamp < :period_end
      AND (:customer_state IS NULL
           OR COALESCE(NULLIF(c.customer_state, ''), 'UNKNOWN') = :customer_state)
), classified AS (
    SELECT *, CASE
        WHEN order_status IS NULL OR order_status <> 'delivered' THEN 'not_delivered'
        WHEN order_delivered_customer_date IS NULL
          OR order_estimated_delivery_date IS NULL THEN 'invalid_delivery_time'
        WHEN order_delivered_customer_date < order_purchase_timestamp
          OR order_estimated_delivery_date < order_purchase_timestamp THEN 'invalid_time_order'
        ELSE 'eligible'
    END AS reason
    FROM cohort
)
SELECT customer_state,
       COUNT(*) AS cohort_order_count,
       SUM(reason = 'eligible') AS eligible_order_count,
       SUM(CASE WHEN reason = 'eligible'
                 AND date(order_delivered_customer_date) > date(order_estimated_delivery_date)
                THEN 1 ELSE 0 END) AS late_order_count,
       SUM(reason <> 'eligible') AS excluded_order_count,
       SUM(reason = 'not_delivered') AS not_delivered,
       SUM(reason = 'invalid_delivery_time') AS invalid_delivery_time,
       SUM(reason = 'invalid_time_order') AS invalid_time_order,
       1.0 * SUM(CASE WHEN reason = 'eligible'
                       AND date(order_delivered_customer_date) > date(order_estimated_delivery_date)
                      THEN 1 ELSE 0 END)
           / NULLIF(SUM(reason = 'eligible'), 0) AS late_rate
FROM classified
GROUP BY customer_state
ORDER BY customer_state;
