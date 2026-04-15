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
    """
    Birden fazla aday güzergah üretir ve en iyisini seçer.

    generate_candidates() şu an deterministik tek plan döndürmektedir.
    Monte Carlo sampling implementasyonu bu metodun içine yazılacak;
    dışarıya açık arayüz (parametre ve dönüş tipleri) sabit kalacaktır.
    """

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
        """
        Tek bir gün için 500 adet random candidate üretir.
        Her candidate 4–9 arası POI içerir.
        """

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
        """
        Gün gün candidate üretir, en iyi planı oluşturur.
        """

        remaining_pois = list(pois)
        day_plans: list[DayPlan] = []

        for day_index in range(1, prefs.trip_days + 1):

            if len(remaining_pois) < 4:
                break

            # 🔹 candidate üret
            candidates: list[list[Poi]] = self.generate_candidates(
                remaining_pois, constraints
            )

            # 🔹 best seç
            best_candidate: list[Poi] = self.select_best_from_candidates(
                candidates, constraints, prefs
            )

            if not best_candidate:
                break

            # 🔹 DayPlan oluştur
            day_plan = self.itinerary_builder.build_day_plan(
                pois=best_candidate,
                day_index=day_index,
            )

            day_plans.append(day_plan)

            # havuzdan çıkar
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
        """
        Candidate'leri skorlar ve en yüksek skorlu olanı döner.
        """

        if not candidates:
            return None

        # 🔹 score hesapla (tek sefer)
        scored_candidates = [
            (cand, self._score(cand, constraints, prefs))
            for cand in candidates
        ]

        # 🔹 en yüksek skoru seç
        best_candidate, best_score = max(
            scored_candidates,
            key=lambda x: x[1]
        )

        return best_candidate

    def _score(self, candidate, constraints, prefs):

        if len(candidate) < 2:
            return 0

        # -------------------------
        # 1. ROUTE ORDER (nearest neighbor)
        # -------------------------
        remaining = candidate[:]
        route = [remaining.pop(0)]

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

        # OSRM approx
        total_distance *= 1.65

        # -------------------------
        # 3. DISTANCE SCORE (target proximity)
        # -------------------------
        target = constraints.max_daily_distance / 1000  # metre → km

        distance_diff = abs(target - total_distance)
        distance_score = 1 / (1 + distance_diff)

        # -------------------------
        # 4. VARIANCE SCORE
        # -------------------------
        if len(segment_distances) > 1:
            var = variance(segment_distances)
        else:
            var = 0

        variance_score = 1 / (1 + var)

        # -------------------------
        # 5. POPULARITY SCORE
        # -------------------------
        pop_scores = []
        for poi in route:
            rating = poi.google_rating or 0
            reviews = poi.google_reviews_total or 0
            pop = rating + math.log(1 + reviews)
            pop_scores.append(pop)

        avg_popularity = sum(pop_scores) / len(pop_scores)

        # normalize (soft cap)
        popularity_score = avg_popularity / 10

        # -------------------------
        # 6. CATEGORY DIVERSITY
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
        diversity_score = len(categories) / len(route)

        # -------------------------
        # 7. POI COUNT
        # -------------------------
        count_score = len(route) / constraints.max_pois_per_day

        # -------------------------
        # 8. FINAL SCORE
        # -------------------------
        score = (
            0.30 * distance_score +
            0.15 * variance_score +
            0.25 * popularity_score +
            0.15 * diversity_score +
            0.15 * count_score
        )

        return score

    def _distance(self, p1, p2):
        R = 6371

        lat1, lon1 = p1.location.latitude, p1.location.longitude
        lat2, lon2 = p2.location.latitude, p2.location.longitude

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c  # km