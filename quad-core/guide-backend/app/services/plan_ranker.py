"""
Plan puanlama stratejileri — aday güzergahları değerlendirerek en iyisini seçer.

Strateji deseni: PlanRanker ABC'si implement edilerek farklı puanlama
algoritmaları çalışma zamanında değiştirilebilir.
"""
from abc import ABC, abstractmethod

from app.models.route import Itinerary
from app.schemas.travel import TravelConstraints, TravelPreferences


class PlanRanker(ABC):
    """Bir aday güzergaha sayısal puan veren soyut puanlayıcı."""

    @abstractmethod
    def score(
        self,
        candidate: Itinerary,
        prefs: TravelPreferences,
        constraints: TravelConstraints,
    ) -> float:
        """
        Güzergahı puanlar; yüksek puan daha iyi planı ifade eder.
        Karşılaştırma için kullanılır — mutlak değeri anlam taşımaz.
        """
        ...


class HeuristicPlanRanker(PlanRanker):
    """
    Temel sezgisel puanlama:
      + Günler arası kategori çeşitliliği ödüllendirilir
        (farklı kategorilerdeki POI sayısı kadar puan eklenir)
      - Günlük maksimum mesafeyi aşan her gün için ceza uygulanır
    """

    def score(
        self,
        candidate: Itinerary,
        prefs: TravelPreferences,
        constraints: TravelConstraints,
    ) -> float:
        if not candidate.days:
            return 0.0

        # Mesafe aşımı cezası: her ihlal eden gün için -1.0
        penalty = 0.0
        for day in candidate.days:
            if day.route_segment:
                if day.route_segment.distance > constraints.max_daily_distance:
                    penalty += 1.0

        # Çeşitlilik bonusu: güzergah genelinde kaç farklı kategori var
        diversity = len({
            c
            for day in candidate.days
            for poi in day.pois
            for c in [
                poi.sub_category_1,
                poi.sub_category_2,
                poi.sub_category_3,
                poi.sub_category_4,
            ]
            if c
        })

        return diversity - penalty
