def brier_score(predictions: list[float], outcomes: list[int]) -> float:
    if not predictions or len(predictions) != len(outcomes):
        return 0.0
    return sum(
        (prediction - outcome) ** 2
        for prediction, outcome in zip(predictions, outcomes, strict=True)
    ) / len(predictions)


def expected_calibration_error(
    predictions: list[float], outcomes: list[int], bins: int = 10
) -> float:
    if not predictions:
        return 0.0
    total = 0.0
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins

        def in_bin(probability: float) -> bool:
            return (
                lower <= probability <= upper if index == bins - 1 else lower <= probability < upper
            )

        selected = [(p, o) for p, o in zip(predictions, outcomes, strict=True) if in_bin(p)]
        if selected:
            confidence = sum(p for p, _ in selected) / len(selected)
            accuracy = sum(o for _, o in selected) / len(selected)
            total += len(selected) / len(predictions) * abs(confidence - accuracy)
    return total
