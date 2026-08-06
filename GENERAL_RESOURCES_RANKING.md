# General Resources: Feedback, Ranking and Review Selection

This document describes the current implementation for `general_resources`.
Course-detail resources are not included.

## 1. What each feedback field does

### Star rating

Users can give 1–5 stars. The star rating contributes to the resource's
recommended score through a Bayesian rating. A simple average is deliberately
not used, so a resource with one 5-star rating cannot immediately outrank a
resource with many consistently good ratings.

### Helpful percentage selector

Users select one of four levels:

| Selection | Stored value | Meaning |
|---|---:|---|
| 😕 25% | 1 | Barely helpful |
| 😐 50% | 2 | Partly helpful |
| 🙂 75% | 3 | Mostly helpful |
| 🤩 100% | 4 | Highly helpful |

Values 3 and 4 count as a positive helpful signal for resource ranking.
The resource card's helpful percentage is calculated from the average helpful
level: `average_helpfulness / 4 * 100`.

### Quick tags

Tags such as `Easy to understand`, `Complete syllabus`, `Outdated`, and
`Missing topics` help users understand the resource quickly. They are shown in
the feedback/review area but currently do not directly change the recommended
score.

### Written review

The written review gives context that stars cannot provide. Reviews are shown
in the resource modal and can be edited by the same anonymous user. Written
review text currently does not directly increase or decrease the resource
ranking score.

## 2. Recommended resource formula

The default `Recommended` order uses this weighted score:

```text
Recommended Score =
    35% * Bayesian Rating
  + 30% * Wilson Helpful Score
  + 25% * Freshness Score
  + 10% * Normalized Log View Score
```

Every component is normalized approximately to the range 0–1 before the
weights are applied. The final score is cached, so it is not recalculated from
scratch on every page request. The current ranking cache lifetime is 5 minutes.

### Bayesian Rating

The implementation uses a prior rating of `4.0` and a prior count of `3`:

```text
Bayesian Average =
  ((rating_count / (rating_count + 3)) * actual_average
   + (3 / (rating_count + 3)) * 4.0) / 5.0
```

This gives new resources a reasonable starting value while gradually trusting
their actual ratings as more users rate them.

### Wilson Helpful Score

For helpfulness, a positive vote means helpfulness level 3 or 4. The positive
vote ratio is adjusted using the Wilson lower-bound confidence score with
`z = 1.96` (approximately 95% confidence).

This prevents a resource with one positive helpful vote from automatically
beating a resource with many consistently positive helpful votes.

### Freshness Score

Recently updated resources receive a small boost:

```text
age_days = days since updated_at
Freshness = 1 / (1 + age_days / 180)
```

If a resource has no update timestamp, a conservative fallback freshness value
of `0.35` is used.

### View Score

Views use a logarithmic scale so very popular resources do not dominate every
other signal:

```text
Normalized Log Views = min(1, log10(views + 1) / 6)
```

## 3. Available sorting options

| Sort option | Actual order |
|---|---|
| Recommended | Weighted recommended score above |
| Top Rated | Bayesian rating, then rating count |
| Most Helpful | Wilson helpful score, then helpful vote count |
| Latest | Latest `updated_at` timestamp |
| Most Viewed | Total view count |

## 4. Badge selection

Only one badge is shown. The application checks badges in this order:

1. `🎯 Exam Favorite` — at least 3 helpful responses and at least 80% helpfulness.
2. `📈 Trending` — at least 5 recent views and at least 60% of the highest recent-view count.
3. `🔥 Most Helpful` — at least 3 helpful responses and Wilson helpful score of at least 0.55.
4. `⭐ Top Rated` — at least 3 star ratings and Bayesian rating of at least 0.78.

The first matching badge wins. This is why only one badge appears on a card.

## 5. Review helpful votes

Users can click `👍 Helpful` on an individual written review. The vote is
stored in `general_resource_review_votes` using the anonymous cookie identity.

The same anonymous user can toggle their vote. Each review displays its helpful
vote count, and reviews are ordered as follows:

```text
highest review helpful count first
then newest updated review first
```

Review helpful votes currently improve the order of reviews inside the modal;
they do not directly change the parent resource's Recommended Score. This
keeps a single review from artificially changing the resource ranking.

## 6. Anonymous identity and spam control

No login is required. The application uses:

- `mh_anon_id` browser cookie for the normal anonymous identity.
- A privacy-safe hashed IP fallback when the cookie is unavailable.

Users may edit written review text and quick tags without waiting. Changing
the star rating or helpfulness level is limited by the 6-hour cooldown for the
same resource and anonymous identity.

## 7. Edit flow

1. User submits feedback.
2. The form changes to `Edit your feedback`.
3. Clicking it pre-fills stars, helpfulness, tags, and review text.
4. The button changes to `Update feedback`.
5. Review/tag-only edits are allowed immediately.
6. Star/helpfulness changes are checked against the 6-hour cooldown.

## 8. Practical interpretation

The best exam resource is not simply the one with the highest average rating.
The system prefers resources that have:

- consistently good ratings,
- reliable helpful responses,
- recent maintenance,
- and meaningful usage.

Written reviews and review helpful votes help users choose the best explanation
or opinion inside the resource modal, while the parent resource ranking stays
stable and harder to manipulate.
