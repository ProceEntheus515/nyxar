class RiskScoreEngine:
    """Motor matemático de evaluación de Riesgo (Risk Score) con Inercia"""

    def calcular_nuevo_score(
        self,
        score_actual: int,
        anomalia_score: float,      # 0.0-1.0 del baseline
        enrichment_score: float,    # 0.0-1.0 según reputación
        patron_score: float,        # 0.0-1.0 si algún patrón disparó
        historial_clean_days: int   # días consecutivos sin anomalías
    ) -> int:
        
        # Factor de inercia: si el score fue alto recientemente, baja más lento
        decay_rate = 0.85 if score_actual > 60 else 0.70
        
        # Score base por los factores del evento actual
        evento_score = (
            anomalia_score * 30 +
            enrichment_score * 40 +
            patron_score * 30
        )
        
        # Historial limpio baja el score más rápido
        clean_bonus = min(historial_clean_days * 5, 30)
        
        # Nuevo score: mezcla ponderada de actual y nuevo evento
        nuevo = score_actual * decay_rate + evento_score * (1 - decay_rate)
        nuevo = max(0, nuevo - clean_bonus)
        
        return min(100, int(nuevo))

    def get_severidad(self, score: int) -> tuple[str, str]:
        """Retorna (nivel, color_hex) según umbrales formales"""
        if score >= 80:
            return ("critica", "#FF4757") # Pastel Red
        elif score >= 60:
            return ("alta", "#FFA502")    # Orange
        elif score >= 40:
            return ("media", "#FFDD57")   # Yellow
        elif score >= 20:
            return ("baja", "#7BED9F")    # Light Green
        else:
            return ("info", "#70A1FF")    # Light Blue
