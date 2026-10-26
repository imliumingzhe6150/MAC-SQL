-- All order statuses; normalized payment_value_cents, no installment multiplication.
WITH cohort AS (
    SELECT * FROM orders
    WHERE order_purchase_timestamp >= :period_start
      AND order_purchase_timestamp < :period_end
)
SELECT p.payment_type,
       COUNT(*) AS payment_record_count,
       COUNT(DISTINCT p.order_id) AS matched_order_count,
       SUM(p.payment_value_cents IS NULL) AS invalid_payment_count,
       SUM(p.payment_value_cents) AS amount_cents,
       (SELECT COUNT(*) FROM cohort) AS cohort_order_count,
       (SELECT COUNT(*) FROM cohort o WHERE NOT EXISTS (
           SELECT 1 FROM order_payments p2 WHERE p2.order_id = o.order_id
       )) AS missing_payment_order_count
FROM cohort o JOIN order_payments p ON p.order_id = o.order_id
GROUP BY p.payment_type
ORDER BY p.payment_type;
