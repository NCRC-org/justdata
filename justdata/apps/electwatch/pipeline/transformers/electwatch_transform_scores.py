"""ElectWatch pipeline: convert raw involvement scores into 1-100 percentile-rank scores."""
import logging

logger = logging.getLogger(__name__)


def _normalize_scores_to_zscore(coordinator):
    """Convert raw involvement scores to percentile rank normalized to 1-100 range."""
    raw_scores = [(i, o.get('involvement_score', 0) or 0) for i, o in enumerate(coordinator.officials_data)]

    if len(raw_scores) < 2:
        return

    sorted_scores = sorted(raw_scores, key=lambda x: (x[1], coordinator.officials_data[x[0]].get('name', '')))
    n = len(sorted_scores)

    rank_lookup = {}
    current_rank = 0
    prev_score = None
    prev_percentile = None

    for rank, (idx, score) in enumerate(sorted_scores):
        if score != prev_score:
            if score == 0:
                percentile = 1
            else:
                percentile = round(((rank + 1) / n) * 99 + 1)
            prev_score = score
            prev_percentile = percentile
        else:
            percentile = prev_percentile

        rank_lookup[idx] = percentile

    with_activity = sum(1 for i, s in raw_scores if s > 0)
    without_activity = n - with_activity
    logger.info(f"Score normalization: {n} officials ({with_activity} with activity, {without_activity} without)")

    for i, official in enumerate(coordinator.officials_data):
        raw_score = official.get('involvement_score', 0)
        percentile = rank_lookup.get(i, 50)

        official['raw_score'] = raw_score
        official['involvement_score'] = percentile
        official['percentile_rank'] = percentile

        if 'score_breakdown' in official:
            official['score_breakdown']['raw_score'] = raw_score
            official['score_breakdown']['percentile'] = percentile

