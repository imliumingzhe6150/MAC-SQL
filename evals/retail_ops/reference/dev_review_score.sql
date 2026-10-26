-- Valid candidates ranked according to the published v1 contract.
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY order_id
        ORDER BY review_answer_timestamp DESC, review_id ASC,
                 review_score_int ASC, source_row ASC
    ) AS choice,
    COUNT(*) OVER (PARTITION BY order_id) AS candidate_count
    FROM order_reviews
    WHERE review_score_int BETWEEN 1 AND 5 AND review_answer_timestamp IS NOT NULL
), raw_orders AS (
    SELECT DISTINCT order_id FROM order_reviews
)
SELECT c.customer_state,
       COUNT(*) AS target_order_count,
       COUNT(r.order_id) AS reviewed_order_count,
       COALESCE(SUM(r.review_score_int <= 2), 0) AS low_score_order_count,
       COALESCE(SUM(r.review_score_int), 0) AS score_sum,
       SUM(raw.order_id IS NULL) AS no_review_order_count,
       SUM(raw.order_id IS NOT NULL AND r.order_id IS NULL) AS only_invalid_review_order_count,
       COALESCE(SUM(r.candidate_count > 1), 0) AS multiple_candidate_order_count
FROM orders o JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN ranked r ON r.order_id = o.order_id AND r.choice = 1
LEFT JOIN raw_orders raw ON raw.order_id = o.order_id
WHERE o.order_purchase_timestamp >= :period_start
  AND o.order_purchase_timestamp < :period_end
  AND o.order_status = 'delivered' AND c.customer_state IN ('SP', 'RJ')
GROUP BY c.customer_state
ORDER BY c.customer_state;
