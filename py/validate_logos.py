from typing import Literal

ValidationResult = Literal[
    "correct",      # Found the right logo (true positive)
    "wrong",        # Found something, but not the logo (false positive)  
    "missed",       # Should have found a logo but didn't (false negative)
    "not_working"   # Site is dead/broken (not applicable)
]


def calculate_metrics(test_cases):
    """Calculate precision and recall from manual validation results."""
    
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    not_working_sites = 0
    
    for _, result in test_cases:
        if result == "correct":
            true_positives += 1
        elif result == "wrong":
            false_positives += 1
        elif result == "missed":
            false_negatives += 1
        elif result == "not_working":
            not_working_sites += 1
    
    if (true_positives + false_positives) > 0:
        precision = true_positives / (true_positives + false_positives)
    else:
        precision = 0
        
    if (true_positives + false_negatives) > 0:
        recall = true_positives / (true_positives + false_negatives)
    else:
        recall = 0
    
    if (precision + recall) > 0:
        f1_score = 2 * (precision * recall) / (precision + recall)
    else:
        f1_score = 0
    
    return {
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'not_working_sites': not_working_sites,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score
    }


def main():
    test_cases = [
        ("bossrevolution.com", "correct"),
        ("acquisio.com", "correct"),
        ("myway.com", "correct"),
        ("simplereach.com", "correct"),
        ("one.com", "wrong"),
        ("dish.com", "correct"),
        ("etoncorp.com", "correct"),
        ("simplehelix.com", "correct"),
        ("sendible.com", "correct"),
        ("name.com", "wrong"),
        ("net.com", "not_working"),
        ("sitepal.com", "correct"),
        ("digitaljournal.com", "correct"),
        ("atlanticbt.com", "correct"),
        ("pages05.net", "correct"),
        ("unitrends.com", "wrong"),
        ("niu.edu", "correct"),
        ("flipsnack.com", "correct"),
        ("flurry.com", "correct"),
        ("seomoz.org", "wrong"),
    ]
    
    metrics = calculate_metrics(test_cases)
    
    print(f"Total cases: {len(test_cases)}")
    print(f"True positives: {metrics['true_positives']}")
    print(f"False positives: {metrics['false_positives']}")
    print(f"False negatives: {metrics['false_negatives']}")
    print(f"Not working sites: {metrics['not_working_sites']}")
    print(f"Precision: {metrics['precision']:.2%}")
    print(f"Recall: {metrics['recall']:.2%}")
    print(f"F1 Score: {metrics['f1_score']:.2%}")


if __name__ == "__main__":
    main()
