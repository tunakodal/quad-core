"""
Monte Carlo güzergah planlayıcı — rastgele örnekleme ile aday planlar üretir
ve en yüksek puanlıyı PlanRanker aracılığıyla seçer.
"""
from typing import Any

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

    """Monte Carlo yontemiyle cok gunluk gezi plani olusturan planlayici."""
    def __init__(
        self,
        itinerary_builder: ItineraryBuilder,
        plan_ranker: PlanRanker,
        max_iterations: int = 100,
        random_seed: int | None = None,
    ):
        """Planlayici bagimliliklerini ve iterasyon parametrelerini alir."""
        self.itinerary_builder = itinerary_builder
        self.plan_ranker = plan_ranker
        self.max_iterations = max_iterations
        self.random_seed = random_seed

    def generate_candidates(
        self,
        pois: list[Poi],
        constraints: TravelConstraints,
    ) -> list[list[Poi]]:

        """500 rastgele POI kombinasyonu uretir; her biri gunluk plan adayidir."""
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

        """POI listesinden gun gune en iyi itinerary'yi olusturur."""
        remaining_pois = list(pois)
        day_plans: list[DayPlan] = []

        for day_index in range(1, prefs.trip_days + 1):

            if len(remaining_pois) < 4:
                break

            best_candidate = self._select_with_retries(
                remaining_pois, constraints, prefs
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

    def _select_with_retries(
            self,
            pois: list[Poi],
            constraints: TravelConstraints,
            prefs: TravelPreferences,
            max_retries: int = 3,
    ) -> list[Poi] | None:
        """
        Her denemede 500 aday üret, skorla sırala, ilk 10'a bak.
        1) duration <= 420 mi?  Değilse geç.
        2) mesafe target * [0.75, 1.25] arasında mı?  Değilse geç.
        İkisini de geçen ilk adayı döndür.
        max_retries kadar tekrar dene, bulamazsa en iyi skoru döndür.
        """

        MAX_DAILY_DURATION = 420
        target_km = constraints.max_daily_distance / 1000
        dist_lo = target_km * 0.75
        dist_hi = target_km * 1.25

        TOP_N = 10
        fallback = None

        for attempt in range(max_retries):
            candidates = self.generate_candidates(pois, constraints)
            if not candidates:
                return None

            scored = [
                (cand, *self._score(cand, constraints, prefs))
                for cand in candidates
            ]
            scored.sort(key=lambda x: x[1], reverse=True)

            # Fallback olarak ilk denemede en iyi skoru sakla
            if fallback is None and scored:
                fallback = scored[0][2]

            for _, score, route in scored[:TOP_N]:
                if score <= 0:
                    continue

                # 1) Duration kontrolü
                total_duration = sum(p.estimated_visit_duration for p in route)
                if total_duration > MAX_DAILY_DURATION:
                    continue

                # 2) Mesafe kontrolü
                total_dist = self._route_distance_km(route)
                if not (dist_lo <= total_dist <= dist_hi):
                    continue

                return route

        # Hiçbir şey uymadıysa fallback
        return fallback

    def _route_distance_km(self, route: list[Poi]) -> float:
        """Route'un toplam mesafesini km cinsinden hesaplar (1.65 çarpanlı)."""
        total = 0.0
        for i in range(len(route) - 1):
            total += self._distance(route[i], route[i + 1])
        return total * 1.65

    def select_best_from_candidates(
            self,
            candidates: list[list[Poi]],
            constraints: TravelConstraints,
            prefs: TravelPreferences,
    ) -> Any | None:

        """Onceden uretilmis aday listesinden en iyi plani secer."""
        if not candidates:
            return None

        scored_candidates = [
            (cand, *self._score(cand, constraints, prefs))
            for cand in candidates
        ]

        # Skora göre azalan sırala
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        MAX_DAILY_DURATION = 420  # 7 saat

        for _, score, route in scored_candidates:
            if score <= 0:
                break
            total_duration = sum(p.estimated_visit_duration for p in route)
            if total_duration <= MAX_DAILY_DURATION:
                return route

        # Hiçbiri 420'nin altında değilse en iyiyi yine de dön
        return scored_candidates[0][2] if scored_candidates else None

    def _score(self, candidate, constraints, prefs):

        """Adayi puanlar ve nearest-neighbor ile optimize edilmis rota sirasi doner."""
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
        DATASET_MIN_POP = 1.8022
        DATASET_MAX_POP = 57.9995

        pop_scores = []
        for poi in route:
            rating = poi.google_rating or 0
            reviews = poi.google_reviews_total or 0
            pop = rating * math.log(1 + reviews)
            pop_scores.append(pop)

        avg_pop = sum(pop_scores) / len(pop_scores)
        popularity_score = (avg_pop - DATASET_MIN_POP) / (DATASET_MAX_POP - DATASET_MIN_POP)
        popularity_score = max(0.0, min(1.0, popularity_score))

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
                0.20 * variance_score +
                0.25 * popularity_score +
                0.05 * diversity_score +
                0.10 * count_score
        )

        return score, route

    @staticmethod
    def _distance_raw(lat1, lng1, lat2, lng2):
        """Iki koordinat arasindaki mesafeyi km cinsinden hesaplar (Haversine)."""
        R = 6371
        dlat = radians(lat2 - lat1)
        dlng = radians(lng2 - lng1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def _distance(self, p1, p2):
        """Iki Poi nesnesi arasindaki mesafeyi km cinsinden doner."""
        return self._distance_raw(
            p1.location.latitude, p1.location.longitude,
            p2.location.latitude, p2.location.longitude,
        )