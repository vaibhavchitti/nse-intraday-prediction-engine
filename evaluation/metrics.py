from __future__ import annotations

from collections import defaultdict


def evaluate_predictions(actual, predicted):
    """Compute core classification metrics for a binary or 3-class prediction task."""
    labels = ["UP", "DOWN", "FLAT"]
    actual_list = list(actual)
    predicted_list = list(predicted)

    confusion = {label: {other: 0 for other in labels} for label in labels}
    for true_label, pred_label in zip(actual_list, predicted_list):
        if true_label not in labels or pred_label not in labels:
            continue
        confusion[true_label][pred_label] += 1

    total = max(len(actual_list), 1)
    correct = sum(confusion[label][label] for label in labels)
    accuracy = correct / total

    precision = {}
    recall = {}
    f1 = {}
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in labels if other != label)
        fn = sum(confusion[label][other] for other in labels if other != label)

        precision[label] = tp / (tp + fp) if (tp + fp) else 0.0
        recall[label] = tp / (tp + fn) if (tp + fn) else 0.0
        f1[label] = 2 * precision[label] * recall[label] / (precision[label] + recall[label]) if (precision[label] + recall[label]) else 0.0

    return {
        "accuracy": float(accuracy),
        "n_samples": int(total),
        "coverage": 1.0,
        "confusion": confusion,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "balanced_accuracy": sum(recall.values()) / len(labels) if labels else 0.0,
    }
