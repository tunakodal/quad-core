"""
Monte Carlo güzergah planlayıcı — rastgele örnekleme ile aday planlar üretir
ve en yüksek puanlıyı PlanRanker aracılığıyla seçer.
"""

from app.models.poi import Poi
from app.models.route import Itinerary
from app.schemas.travel import TravelConstraints, TravelPreferences
from app.services.itinerary_builder import ItineraryBuilder
from app.services.plan_ranker import PlanRanker
from app.models.route import DayPlan
import random
import math
from statistics import variance
from math import radians, sin, cos, sqrt, atan2


class MonteCarloItineraryPlanner:

    def __init__(
        self,
        itinerary_builder: ItineraryBuilder,
        plan_ranker: PlanRanker,
        max_iterations: int = 100,
        random_seed: int | None = None,
    ):
        self.itinerary_builder = itinerary_builder
        self.plan_ranker = plan_ranker
        self.max_iterations = max_iterations
        self.random_seed = random_seed

    def generate_candidates(
        self,
        pois: list[Poi],
        constraints: TravelConstraints,
    ) -> list[list[Poi]]:

        if len(pois) < 4:
            return []

        candidates: list[list[Poi]] = []

        min_k = 4
        max_k = min(constraints.max_pois_per_day, len(pois))

        for _ in range(500):
            k = random.randint(min_k, max_k)
            sample = random.sample(pois, k)
            candidates.append(sample)

        return candidates

    def select_best(
        self,
        pois: list[Poi],
        constraints: TravelConstraints,
        prefs: TravelPreferences,
    ) -> Itinerary:

        remaining_pois = list(pois)
        day_plans: list[DayPlan] = []

        for day_index in range(1, prefs.trip_days + 1):

            if len(remaining_pois) < 4:
                break

            candidates = self.generate_candidates(remaining_pois, constraints)

            best_candidate = self.select_best_from_candidates(
                candidates, constraints, prefs
            )

            if not best_candidate:
                break

            day_plan = self.itinerary_builder.build_day_plan(
                pois=best_candidate,
                day_index=day_index,
            )

            day_plans.append(day_plan)

            selected_ids = {poi.id for poi in best_candidate}
            remaining_pois = [
                poi for poi in remaining_pois if poi.id not in selected_ids
            ]

        return self.itinerary_builder.build_itinerary_from_days(day_plans)

    def select_best_from_candidates(
        self,
        candidates: list[list[Poi]],
        constraints: TravelConstraints,
        prefs: TravelPreferences,
    ) -> list[Poi]:

        if not candidates:
            return None

        scored_candidates = [
            (cand, *self._score(cand, constraints, prefs))
            for cand in candidates
        ]

        # (original_cand, score, sorted_route)
        best = max(scored_candidates, key=lambda x: x[1])

        return best[2]  # sıralı route

    def _score(self, candidate, constraints, prefs):

        if len(candidate) < 2:
            return 0, candidate

        # -------------------------
        # 1. ROUTE ORDER
        # -------------------------
        n = len(candidate)
        avg_lat = sum(p.location.latitude for p in candidate) / n
        avg_lng = sum(p.location.longitude for p in candidate) / n

        start = max(candidate, key=lambda p: self._distance_raw(
            avg_lat, avg_lng, p.location.latitude, p.location.longitude
        ))

        remaining = [p for p in candidate if p.id != start.id]
        route = [start]

        while remaining:
            last = route[-1]
            next_poi = min(
                remaining,
                key=lambda p: self._distance(last, p)
            )
            route.append(next_poi)
            remaining.remove(next_poi)

        # -------------------------
        # 2. DISTANCE CALCULATION
        # -------------------------
        segment_distances = []
        total_distance = 0

        for i in range(len(route) - 1):
            d = self._distance(route[i], route[i + 1])
            segment_distances.append(d)
            total_distance += d

        total_distance *= 1.65

        # -------------------------
        # 3. HARD CAP — target'ın 2 katını aşarsa direkt ele
        # -------------------------
        target = constraints.max_daily_distance / 1000

        if total_distance > target * 2:
            return 0, route

        # -------------------------
        # 4. DISTANCE SCORE — gaussian
        # -------------------------
        sigma = target * 0.3
        distance_score = math.exp(-((total_distance - target) ** 2) / (2 * sigma ** 2))

        # -------------------------
        # 5. VARIANCE SCORE
        # -------------------------
        if len(segment_distances) > 1:
            mean_seg = sum(segment_distances) / len(segment_distances)
            if mean_seg > 0:
                std_seg = math.sqrt(variance(segment_distances))
                cv = std_seg / mean_seg
                variance_score = 1 / (1 + cv)
            else:
                variance_score = 1.0
        else:
            variance_score = 1.0

        # -------------------------
        # 6. POPULARITY SCORE
        # -------------------------
        pop_scores = []
        for poi in route:
            rating = poi.google_rating or 0
            reviews = poi.google_reviews_total or 0
            pop = rating * math.log(1 + reviews)
            pop_scores.append(pop)

        min_pop = min(pop_scores)
        max_pop = max(pop_scores)
        if max_pop > min_pop:
            popularity_score = (
                    (sum(pop_scores) / len(pop_scores) - min_pop) / (max_pop - min_pop)
            )
        else:
            popularity_score = 1.0

        # -------------------------
        # 7. CATEGORY DIVERSITY
        # -------------------------
        categories = {
            c
            for poi in route
            for c in [
                poi.sub_category_1,
                poi.sub_category_2,
                poi.sub_category_3,
                poi.sub_category_4,
            ]
            if c
        }
        max_possible_cats = len(route) * 4
        diversity_score = min(len(categories) / max_possible_cats, 1.0)

        # -------------------------
        # 8. POI COUNT
        # -------------------------
        count_score = len(route) / constraints.max_pois_per_day

        # -------------------------
        # 9. FINAL SCORE — distance ağırlığı artırıldı
        # -------------------------
        score = (
                0.40 * distance_score +
                0.10 * variance_score +
                0.25 * popularity_score +
                0.10 * diversity_score +
                0.15 * count_score
        )

        return score, route

    @staticmethod
    def _distance_raw(lat1, lng1, lat2, lng2):
        R = 6371
        dlat = radians(lat2 - lat1)
        dlng = radians(lng2 - lng1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def _distance(self, p1, p2):
        return self._distance_raw(
            p1.location.latitude, p1.location.longitude,
            p2.location.latitude, p2.location.longitude,
        )