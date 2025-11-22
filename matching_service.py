def calculate_match_score(lost_item, found_item):
    """Calculate similarity score between lost and found items"""
    score = 0
    
    # Compare item types (highest weight)
    if lost_item.get("item_type", "").lower() == found_item.get("item_type", "").lower():
        score += 40
    
    # Compare colors
    if lost_item.get("color", "").lower() in found_item.get("color", "").lower() or \
       found_item.get("color", "").lower() in lost_item.get("color", "").lower():
        score += 25
    
    # Compare brands
    if lost_item.get("brand", "").lower() == found_item.get("brand", "").lower() and lost_item.get("brand", "") != "Unknown":
        score += 20
    
    # Compare features (keyword matching)
    lost_features = set(lost_item.get("features", "").lower().split())
    found_features = set(found_item.get("features", "").lower().split())
    feature_overlap = len(lost_features & found_features)
    if feature_overlap > 0:
        score += min(15, feature_overlap * 5)
    
    return score
