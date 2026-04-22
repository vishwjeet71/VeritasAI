from typing import Optional

def calculate_credibility_score(attrs: dict) -> float:

    if not attrs:
        return 0.5

    component_scores: dict[str, tuple[float, float]] = {}  

    # FACTUAL REPORTING
    factual_score: Optional[float] = None

    val_int = attrs.get("factual_reporting_int")
    if val_int is not None:
        try:
            linear = max(0.0, min(1.0, 1.0 - (float(val_int) - 1.0) / 7.0))
            factual_score = linear ** 1.5                
        except (TypeError, ValueError):
            pass

    if factual_score is None:
        val_str = str(attrs.get("factual_reporting_str") or "").lower().strip()
       
        factual_str_map: dict[str, float] = {
            "very high":      0.93,
            "high":           0.72,
            "mostly factual": 0.49,
            "mixed":          0.21,
            "low":            0.06,
            "very low":       0.01,
        }
        factual_score = factual_str_map.get(val_str)

    if factual_score is not None:
        component_scores["factual"] = (factual_score, 0.37)

    # MBFC CREDIBILITY RATING

    cred_val = str(attrs.get("mbfc_credibility_rating") or "").lower().strip()
    credibility_map: dict[str, float] = {
        "high credibility":     0.90,
        "medium credibility":   0.40,
        "low credibility":      0.12,
        "very low credibility": 0.02,
    }
    cred_score = credibility_map.get(cred_val)
    if cred_score is not None:
        component_scores["credibility"] = (cred_score, 0.25)

    # BIAS RATING

    bias_score: Optional[float] = None

    bias_int = attrs.get("bias_rating_int")
    if bias_int is not None:
        try:
            extremity = abs(float(bias_int)) / 10.0
            bias_score = max(0.0, 1.0 - extremity ** 1.4)
        except (TypeError, ValueError):
            pass

    if bias_score is None:
        bias_str = str(attrs.get("bias_rating_str") or "").lower().strip()
        bias_str_map: dict[str, float] = {
            "center":                   1.00,
            "pro-science":              0.95,
            "left-center":              0.82,
            "right-center":             0.82,
            "left":                     0.58,
            "right":                    0.58,
            "left bias":                0.58,
            "right bias":               0.58,
            "extreme left":             0.20,
            "extreme right":            0.20,
            "conspiracy-pseudoscience": 0.00,
            "satire":                   0.30,
        }
        bias_score = bias_str_map.get(bias_str)

    if bias_score is not None:
        component_scores["bias"] = (bias_score, 0.22)

    # COUNTRY PRESS FREEDOM

    freedom_val = str(attrs.get("mbfc_country_freedom_rating") or "").lower().strip()
    freedom_map: dict[str, float] = {
        "free":             1.00,
        "mostly free":      0.82,
        "moderate freedom": 0.52,
        "not free":         0.15,
    }
    freedom_score = freedom_map.get(freedom_val)
    if freedom_score is not None:
        component_scores["freedom"] = (freedom_score, 0.12)

    # TRAFFIC / POPULARITY

    traffic_val = str(attrs.get("traffic_popularity") or "").lower().strip()
    traffic_map: dict[str, float] = {
        "high traffic":   0.62,
        "medium traffic": 0.52,
        "low traffic":    0.42,
    }
    traffic_score = traffic_map.get(traffic_val)
    if traffic_score is not None:
        component_scores["traffic"] = (traffic_score, 0.025)

    # MEDIA TYPE

    media_val = str(attrs.get("media_type") or "").lower().strip()
    media_map: dict[str, float] = {
        "peer reviewed": 1.00,
        "science":       0.90,
        "newspaper":     0.70,
        "magazine":      0.65,
        "tv":            0.60,
        "television":    0.60,
        "radio":         0.60,
        "online":        0.50,
        "website":       0.50,
        "blog":          0.35,
        "tabloid":       0.20,
        "satire":        0.10,
    }
    media_score = media_map.get(media_val)
    if media_score is not None:
        component_scores["media"] = (media_score, 0.015)

    if not component_scores:
        return 0.5

    total_weight = sum(w for _, w in component_scores.values())
    weighted_sum = sum(s * w for s, w in component_scores.values())

    return round(weighted_sum / total_weight, 4)


if __name__ == "__main__":
    example_1 = {
        "bias_rating_str":            "right-center",
        "bias_rating_int":            2.9,
        "factual_reporting_str":      "mixed",
        "factual_reporting_int":      5.1,
        "country":                    "india",
        "mbfc_country_freedom_rating":"moderate freedom",
        "media_type":                 "newspaper",
        "traffic_popularity":         "high traffic",
        "mbfc_credibility_rating":    "medium credibility",
    }

    example_2 = {
        "bias_rating_str":            None,
        "bias_rating_int":            None,
        "factual_reporting_str":      None,
        "factual_reporting_int":      None,
        "country":                    None,
        "mbfc_country_freedom_rating":None,
        "media_type":                 None,
        "traffic_popularity":         None,
        "mbfc_credibility_rating":    None,
    }

    print(calculate_credibility_score(example_2))
