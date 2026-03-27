import re
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from math import radians, sin, cos, sqrt, atan2
from products.models import Product
from barter.models import ReplaceOption
from accounts.models import UserProfile  # adjust to your app name


# ── Haversine distance (km) ──────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def quoted_join(words):
    return ", ".join('"' + w + '"' for w in words)


# ── Common filler words to skip ──────────────────────────────────────────────
STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "use",
    "used", "year", "years", "old", "new", "good", "great", "very", "also",
    "buy", "sell", "come", "comes", "will", "your", "our", "its", "has",
    "been", "are", "was", "were", "can", "just", "only", "into", "about",
}


def extract_keywords(text):
    """
    Smart keyword extractor that handles:
      - Normal words (len > 3, not stopwords)
      - Tech specs: alphanumeric tokens like i5, i7, 8gb, 16gb, 512gb,
        rtx3080, m2, usb, ssd, hdd, 4k, etc.
      - Numbers like 8, 16, 512 (standalone digits that are likely specs)
    Returns a set of lowercase strings.
    """
    if not text:
        return set()

    text_lower = text.lower()
    keywords   = set()

    # Split on whitespace and common punctuation
    tokens = re.split(r'[\s,./;:()\[\]]+', text_lower)

    for token in tokens:
        token = token.strip("-").strip()
        if not token:
            continue

        # Always keep tech spec patterns regardless of length:
        #   i3 i5 i7 i9, 8gb 16gb 512gb, rtx3080, ssd, hdd, 4k, m1 m2 m3
        if re.match(r'^(i[3579]|[0-9]+gb|[0-9]+tb|[0-9]+mb|rtx\w+|gtx\w+|rx\w+'
                    r'|ssd|hdd|nvme|usb|[0-9]+k|m[123]|r[57]|ryzen\w*'
                    r'|gen[0-9]*|[0-9]+th|[0-9]+hz|[0-9]+mp|[0-9]+w'
                    r'|[0-9]+inch|[0-9]+"|\d+)$', token):
            keywords.add(token)
            continue

        # Normal words: keep if len > 2 and not a stopword
        if len(token) > 2 and token not in STOPWORDS:
            keywords.add(token)

    return keywords


def text_contains_keyword(text, keyword):
    """
    Case-insensitive whole-token match so '8' doesn't match '18' or '8gb'.
    Uses word-boundary aware check.
    """
    if not text or not keyword:
        return False
    # Use regex word boundary for clean matching
    pattern = r'(?<![a-z0-9])' + re.escape(keyword.lower()) + r'(?![a-z0-9])'
    return bool(re.search(pattern, text.lower()))


# ── Match scorer ─────────────────────────────────────────────────────────────
def compute_match(product, replace_options, max_dist_km, dist_km):
    """
    Returns (total_score: int, breakdown: dict).

    Scoring (100 pts total):
      40 — title keyword match
      25 — description keyword match
      20 — category match
      15 — proximity
    """

    title_keywords    = {}   # keyword → [opt labels]
    desc_keywords     = {}   # keyword → [opt labels]
    wanted_categories = {}   # cat_id  → cat_name

    for opt in replace_options:
        label = opt.title or ("option #" + str(opt.id))

        if opt.title:
            for kw in extract_keywords(opt.title):
                title_keywords.setdefault(kw, []).append(label)

        if opt.description:
            for kw in extract_keywords(opt.description):
                desc_keywords.setdefault(kw, []).append(label)

        if opt.category_id:
            cat_name = opt.category.name if opt.category else str(opt.category_id)
            wanted_categories[opt.category_id] = cat_name

    product_title = (product.title or "").lower()
    product_desc  = (product.description or "").lower()

    # ── Title match (40 pts) ─────────────────────────────────────────────────
    title_hits = {
        kw: src for kw, src in title_keywords.items()
        if text_contains_keyword(product_title, kw)
    }
    title_score = round((len(title_hits) / len(title_keywords)) * 40) if title_keywords else 0

    # ── Description match (25 pts) ───────────────────────────────────────────
    all_keywords = {}
    all_keywords.update(title_keywords)
    all_keywords.update(desc_keywords)

    desc_hits = {
        kw: src for kw, src in all_keywords.items()
        if text_contains_keyword(product_desc, kw)
    }
    desc_score = round((len(desc_hits) / len(all_keywords)) * 25) if all_keywords else 0

    # ── Category match (20 pts) ──────────────────────────────────────────────
    category_matched = None
    category_score   = 0
    if product.category_id and product.category_id in wanted_categories:
        category_matched = wanted_categories[product.category_id]
        category_score   = 20

    # ── Proximity (15 pts) ───────────────────────────────────────────────────
    proximity_score = round(max(0, 1 - (dist_km / max_dist_km)) * 15) if max_dist_km > 0 else 0

    total = min(title_score + desc_score + category_score + proximity_score, 100)

    # ── Build ranked match reasons ────────────────────────────────────────────
    match_reasons = []

    if title_hits:
        words = list(title_hits.keys())[:5]
        match_reasons.append({
            "criterion":     "title",
            "label":         "Title match",
            "score":         title_score,
            "max_score":     40,
            "matched_terms": words,
            "detail":        "Title contains: " + quoted_join(words),
        })

    if desc_hits:
        words = list(desc_hits.keys())[:5]
        match_reasons.append({
            "criterion":     "description",
            "label":         "Description match",
            "score":         desc_score,
            "max_score":     25,
            "matched_terms": words,
            "detail":        "Description contains: " + quoted_join(words),
        })

    if category_matched:
        match_reasons.append({
            "criterion":     "category",
            "label":         "Category match",
            "score":         category_score,
            "max_score":     20,
            "matched_terms": [category_matched],
            "detail":        'Same category: "' + category_matched + '"',
        })

    if proximity_score > 0:
        match_reasons.append({
            "criterion":     "proximity",
            "label":         "Nearby",
            "score":         proximity_score,
            "max_score":     15,
            "matched_terms": [],
            "detail":        str(round(dist_km, 1)) + " km away",
        })

    match_reasons.sort(key=lambda r: r["score"], reverse=True)

    breakdown = {
        "title_score":     title_score,
        "desc_score":      desc_score,
        "category_score":  category_score,
        "proximity_score": proximity_score,
        "match_reasons":   match_reasons,
        "top_criterion":   match_reasons[0]["criterion"] if match_reasons else None,
        "top_label":       match_reasons[0]["label"]     if match_reasons else "No match",
    }

    return total, breakdown


# ── Serialiser ───────────────────────────────────────────────────────────────
def serialize_match(product, dist_km, match_score, breakdown):
    thumbnail = None
    first_img = product.images.first()  # adjust related_name if needed
    if first_img:
        try:
            thumbnail = first_img.image.url
        except Exception:
            pass

    owner      = product.owner
    owner_name = (owner.first_name + " " + owner.last_name).strip() or owner.username

    replace_opts = list(
        product.replace_options
        .filter(title__gt="")
        .values_list("title", flat=True)
    )

    return {
        "id":            product.id,
        "title":         product.title,
        "description":   product.description,
        "category":      product.category.name if product.category else None,
        "thumbnail":     thumbnail,
        "owner_name":    owner_name,
        "distance_km":   round(dist_km, 2),
        "match_score":   match_score,
        "match_breakdown": {
            "scores": {
                "title":       breakdown["title_score"],
                "description": breakdown["desc_score"],
                "category":    breakdown["category_score"],
                "proximity":   breakdown["proximity_score"],
            },
            "reasons":       breakdown["match_reasons"],
            "top_criterion": breakdown["top_criterion"],
            "top_label":     breakdown["top_label"],
        },
        "replace_options": replace_opts,
        "status":          product.status,
        "purchase_year":   product.purchase_year,
    }


# ════════════════════════════════════════════════════════════════════════════
# GET /products/scan/<product_id>/?radius=<km>&min_score=<0-100>
# ════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scan_product(request, product_id):
    """
    Scans nearby approved products matching this product's exchange prefs.

    Query params:
      radius    (float km, default 10, max 200)
      min_score (int 0-100, default 0)
    """

    # ── 1. Ownership ─────────────────────────────────────────────────────────
    try:
        owner_product = Product.objects.select_related("category").get(
            id=product_id, owner=request.user
        )
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found or you are not the owner."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # ── 2. Owner location ────────────────────────────────────────────────────
    try:
        owner_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "Profile not found. Please complete your profile."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if owner_profile.latitude is None or owner_profile.longitude is None:
        return Response(
            {"error": "Please add your location in your profile before scanning."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    owner_lat = float(owner_profile.latitude)
    owner_lng = float(owner_profile.longitude)

    # ── 3. Query params ──────────────────────────────────────────────────────
    try:
        radius_km = min(float(request.query_params.get("radius", 10)), 200)
        if radius_km <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return Response(
            {"error": "Invalid radius. Must be a positive number (max 200 km)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    min_score = max(0, min(int(request.query_params.get("min_score", 0)), 100))

    # ── 4. Replace options ───────────────────────────────────────────────────
    replace_options = list(
        owner_product.replace_options
        .select_related("category")
    )

    if not replace_options:
        return Response(
            {"error": "This product has no exchange preferences. Add what you want in return first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── 5. DB pre-filter using smart keywords ────────────────────────────────
    keyword_q = Q()
    for opt in replace_options:
        for kw in extract_keywords(opt.title or ""):
            keyword_q |= Q(title__icontains=kw)
            keyword_q |= Q(description__icontains=kw)
        for kw in extract_keywords(opt.description or ""):
            keyword_q |= Q(title__icontains=kw)
            keyword_q |= Q(description__icontains=kw)
        if opt.category_id:
            keyword_q |= Q(category_id=opt.category_id)

    if not keyword_q:
        return Response([], status=status.HTTP_200_OK)

    candidates = (
        Product.objects
        .filter(keyword_q, status="approved")
        .exclude(owner=request.user)
        .select_related("owner", "category")
        .prefetch_related("replace_options", "images")
        .distinct()
    )

    # ── 6. Distance + scoring ─────────────────────────────────────────────────
    owner_ids   = candidates.values_list("owner_id", flat=True).distinct()
    profile_map = {
        p.user_id: p
        for p in UserProfile.objects.filter(
            user_id__in=owner_ids,
            latitude__isnull=False,
            longitude__isnull=False,
        )
    }

    results = []
    for product in candidates:
        profile = profile_map.get(product.owner_id)
        if not profile:
            continue

        dist_km = haversine(
            owner_lat, owner_lng,
            float(profile.latitude),
            float(profile.longitude),
        )

        if dist_km > radius_km:
            continue

        score, breakdown = compute_match(product, replace_options, radius_km, dist_km)

        if score < min_score:
            continue

        results.append((product, dist_km, score, breakdown))

    # ── 7. Sort: score DESC, distance ASC ────────────────────────────────────
    results.sort(key=lambda x: (-x[2], x[1]))

    # ── 8. Return ────────────────────────────────────────────────────────────
    return Response(
        [serialize_match(p, d, s, b) for p, d, s, b in results],
        status=status.HTTP_200_OK,
    )