from __future__ import annotations

from ledger.forecast_store import ForecastLedger, OutcomeStore


class OutcomeValidator:
    """Validate matured forecasts separately from the immutable prediction record."""

    def __init__(self, ledger: ForecastLedger, outcomes: OutcomeStore):
        self.ledger = ledger
        self.outcomes = outcomes

    def _classify_return(self, value: float, positive_threshold: float = 0.003, negative_threshold: float = -0.003) -> str:
        if value > positive_threshold:
            return "UP"
        if value < negative_threshold:
            return "DOWN"
        return "FLAT"

    def validate_matured_forecast(
        self,
        *,
        forecast_id: str,
        actual_price: float,
        validation_time: str,
        positive_threshold: float = 0.003,
        negative_threshold: float = -0.003,
    ) -> dict:
        forecast = self.ledger.get_prediction(forecast_id)
        reference_price = float(forecast["reference_price"])
        actual_return = (float(actual_price) / reference_price) - 1.0
        outcome_class = self._classify_return(actual_return, positive_threshold, negative_threshold)
        predicted_class = forecast["predicted_class"]
        correct = predicted_class.upper() == outcome_class.upper()

        result = self.outcomes.record_outcome(
            forecast_id=forecast_id,
            outcome_class=outcome_class,
            actual_return=actual_return,
            actual_price=actual_price,
            predicted_class=predicted_class,
            correctness=correct,
            validation_time=validation_time,
        )

        result["forecast_status"] = forecast["forecast_status"]
        result["predicted_class"] = predicted_class
        result["correct"] = bool(correct)
        result["outcome_class"] = outcome_class
        result["actual_return"] = actual_return
        return result
