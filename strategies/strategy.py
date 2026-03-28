def decide_action(probability_up: float, threshold: float = 0.55) -> str:
    """
    Action labels:
    - BUY: probability >= threshold
    - WAIT: 0.50 <= probability < threshold (close call / uncertain)
    - DON'T BUY: probability < 0.50
    """
    if probability_up >= threshold:
        return "BUY"
    if probability_up >= 0.50:
        return "WAIT"
    return "DON'T BUY"


def generate_signal(model, latest_row, threshold=0.55):
    probability_up = float(model.predict_proba([latest_row])[0][1])
    action = decide_action(probability_up, threshold=threshold)
    return action, probability_up
