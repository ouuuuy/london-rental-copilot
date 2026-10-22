def filter_listings(constraints, all_listings):
    """Deterministic filter: matched + excluded with reasons."""
    matched = []
    excluded = []

    budget = constraints.get("budget")
    has_budget = isinstance(budget, int) and budget > 0
    target_beds = constraints.get("beds")
    needs_pets = constraints.get("pets_allowed") is True
    needs_garden = constraints.get("has_garden") is True

    for listing in all_listings:
        reasons = []
        match_tags = []
        price = listing.get("price_pcm", 0)

        if has_budget and price > budget:
            reasons.append(f"£{price - budget} over budget")
        elif has_budget:
            match_tags.append("Budget")

        if target_beds is not None and listing.get("beds") != target_beds:
            reasons.append(f"Has {listing.get('beds')} beds, need {target_beds}")
        elif target_beds is not None:
            match_tags.append("Beds")

        if needs_pets and not listing.get("pets_allowed"):
            reasons.append("No pets allowed")
        elif needs_pets:
            match_tags.append("Pets")

        if needs_garden and not listing.get("has_garden"):
            reasons.append("No garden")
        elif needs_garden:
            match_tags.append("Garden")

        if reasons:
            excluded.append({"id": listing["id"], "title": listing["title"], "reasons": reasons})
        else:
            listing_copy = dict(listing)
            listing_copy["match_tags"] = match_tags
            matched.append(listing_copy)
    return matched, excluded
