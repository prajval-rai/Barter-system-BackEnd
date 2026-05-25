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



# ════════════════════════════════════════════════════════════════════════════
# GET /products/nearby/?radius=<km>&limit=<n>
# ════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def nearby_products(request):
    """
    Returns nearby approved products sorted by distance.

    Query params:
      radius  (float km, default 10, max 200)
      limit   (int,      default 4,  max 50)
    """

    # ── 1. Get requester's location ──────────────────────────────────────────
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "Profile not found. Please complete your profile."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if profile.latitude is None or profile.longitude is None:
        return Response(
            {"error": "Please add your location in your profile before scanning."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    my_lat = float(profile.latitude)
    my_lng = float(profile.longitude)

    # ── 2. Query params ──────────────────────────────────────────────────────
    try:
        radius_km = min(float(request.query_params.get("radius", 10)), 200)
        if radius_km <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return Response(
            {"error": "Invalid radius. Must be a positive number (max 200 km)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        limit = min(int(request.query_params.get("limit", 4)), 50)
        if limit <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return Response(
            {"error": "Invalid limit. Must be a positive integer (max 50)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── 3. Fetch approved products (exclude own) ─────────────────────────────
    candidates = (
        Product.objects
        .filter(status="approved")
        .exclude(owner=request.user)
        .select_related("owner", "category")
        .prefetch_related("images")
    )

    # ── 4. Build owner → profile map ─────────────────────────────────────────
    owner_ids   = candidates.values_list("owner_id", flat=True).distinct()
    profile_map = {
        p.user_id: p
        for p in UserProfile.objects.filter(
            user_id__in=owner_ids,
            latitude__isnull=False,
            longitude__isnull=False,
        )
    }

    # ── 5. Distance filter ───────────────────────────────────────────────────
    nearby = []
    for product in candidates:
        owner_profile = profile_map.get(product.owner_id)
        if not owner_profile:
            continue

        dist_km = haversine(
            my_lat, my_lng,
            float(owner_profile.latitude),
            float(owner_profile.longitude),
        )

        if dist_km <= radius_km:
            nearby.append((product, dist_km))

    # ── 6. Sort by distance ASC, take top N ──────────────────────────────────
    nearby.sort(key=lambda x: x[1])
    nearby = nearby[:limit]

    # ── 7. Serialize ─────────────────────────────────────────────────────────
    def serialize(product, dist_km):
        image = product.images.first()
        thumbnail = image.image.url if image else None

        return {
            "id":            product.id,
            "title":         product.title,
            "thumbnail":     thumbnail,
            "category_name": product.category.name if product.category else None,
            "status":        product.status,
            "distance_km":   round(dist_km, 2),
            "owner": {
                "id":       product.owner.id,
                "username": product.owner.username,
            },
        }

    return Response(
        [serialize(p, d) for p, d in nearby],
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scan_all_my_products(request):
    """
    Scans nearby approved products matching ANY of the user's own products.

    Query params:
      radius    (float km, default 10, max 200)
      min_score (int 0-100, default 0)
      limit     (int,       default 20, max 100)
    """

    # ── 1. Owner location ────────────────────────────────────────────────────
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

    # ── 2. Query params ──────────────────────────────────────────────────────
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

    try:
        limit = min(int(request.query_params.get("limit", 20)), 100)
        if limit <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return Response(
            {"error": "Invalid limit. Must be a positive integer (max 100)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── 3. Fetch all my products with their replace_options AND images ────────
    my_products = (
        Product.objects
        .filter(owner=request.user, status="approved")
        .select_related("category")
        .prefetch_related("replace_options__category", "images")  # ← "images" added
    )

    if not my_products.exists():
        return Response(
            {"error": "You have no approved products to scan from."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── 4. Collect all replace_options across all my products ────────────────
    # Map: replace_option → which of my products it belongs to
    option_to_my_product = {}
    all_replace_options = []

    for my_product in my_products:
        opts = list(my_product.replace_options.select_related("category"))
        for opt in opts:
            option_to_my_product[opt.id] = my_product
            all_replace_options.append(opt)

    if not all_replace_options:
        return Response(
            {"error": "None of your products have exchange preferences set."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── 5. Build keyword query across ALL replace options ────────────────────
    keyword_q = Q()
    for opt in all_replace_options:
        raw_title = (opt.title or "").strip()
        
        # Match full phrase
        keyword_q |= Q(title__icontains=raw_title)
        
        # Match without spaces (JBL Head Phone → JBLHeadPhone — no, but:)
        # Match each word individually  
        for kw in extract_keywords(raw_title):
            keyword_q |= Q(title__icontains=kw)
        
        # ← KEY FIX: also try concatenated pairs
        words = raw_title.split()
        for i in range(len(words) - 1):
            compound = words[i] + words[i+1]          # "Head"+"Phone" = "HeadPhone"
            keyword_q |= Q(title__icontains=compound)  # matches "Headphone"

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

    # ── 6. Build owner → profile map ─────────────────────────────────────────
    owner_ids   = candidates.values_list("owner_id", flat=True).distinct()
    profile_map = {
        p.user_id: p
        for p in UserProfile.objects.filter(
            user_id__in=owner_ids,
            latitude__isnull=False,
            longitude__isnull=False,
        )
    }

    # ── 7. Score each candidate against ALL my products ──────────────────────
    seen = {}  # candidate_id → best result so far

    for candidate in candidates:
        profile = profile_map.get(candidate.owner_id)
        if not profile:
            continue

        dist_km = haversine(
            owner_lat, owner_lng,
            float(profile.latitude),
            float(profile.longitude),
        )

        if dist_km > radius_km:
            continue

        best_score      = -1
        best_breakdown  = {}
        best_my_product = None

        for my_product in my_products:
            my_opts = list(my_product.replace_options.all())
            if not my_opts:
                continue

            score, breakdown = compute_match(candidate, my_opts, radius_km, dist_km)

            if score > best_score:
                best_score      = score
                best_breakdown  = breakdown
                best_my_product = my_product

        if best_score < min_score or best_my_product is None:
            continue

        if candidate.id not in seen or best_score > seen[candidate.id][2]:
            seen[candidate.id] = (candidate, dist_km, best_score, best_breakdown, best_my_product)

    # ── 8. Sort: score DESC, distance ASC ────────────────────────────────────
    results = sorted(seen.values(), key=lambda x: (-x[2], x[1]))[:limit]

    # ── 9. Serialize ─────────────────────────────────────────────────────────
    def serialize(candidate, dist_km, score, breakdown, matched_my_product):
        # "YOU GET" — candidate's own image
        candidate_image = candidate.images.first()
        thumbnail = candidate_image.image.url if candidate_image else None

        # "YOU GIVE" — your own matched product's image
        my_image = matched_my_product.images.first()
        my_product_thumbnail = my_image.image.url if my_image else None

        # replace_options on matched_my_product are plain title strings
        replace_options = [
            opt.title
            for opt in matched_my_product.replace_options.all()
        ]

        return {
            **serialize_match(candidate, dist_km, score, breakdown),
            "thumbnail":            thumbnail,            # candidate's image — "YOU GET"
            "my_product_thumbnail": my_product_thumbnail, # your product's image — "YOU GIVE"
            "replace_options":      replace_options,
            "matched_via": {
                "id":    matched_my_product.id,
                "title": matched_my_product.title,
            },
        }

    return Response(
        [serialize(c, d, s, b, mp) for c, d, s, b, mp in results],
        status=status.HTTP_200_OK,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def debug_scan(request):
    
    # Step 1: Check profile
    try:
        owner_profile = UserProfile.objects.get(user=request.user)
        profile_data = {
            "lat": str(owner_profile.latitude),
            "lng": str(owner_profile.longitude),
        }
    except UserProfile.DoesNotExist:
        return Response({"error": "No profile"})

    # Step 2: My products
    my_products = Product.objects.filter(owner=request.user, status="approved").prefetch_related("replace_options__category", "images")
    my_products_data = [
        {
            "id": p.id,
            "title": p.title,
            "category_id": p.category_id,
            "replace_options": [
                {"id": o.id, "title": o.title, "category_id": o.category_id}
                for o in p.replace_options.all()
            ],
        }
        for p in my_products
    ]

    # Step 3: All candidates (no filter)
    all_candidates = Product.objects.filter(status="approved").exclude(owner=request.user)
    candidates_data = [
        {"id": p.id, "title": p.title, "category_id": p.category_id, "owner_id": p.owner_id}
        for p in all_candidates
    ]

    # Step 4: Build keyword_q and show what it matches
    all_replace_options = []
    for p in my_products:
        for opt in p.replace_options.all():
            all_replace_options.append(opt)

    raw_keywords = []
    for opt in all_replace_options:
        raw_title = (opt.title or "").strip()
        raw_keywords.append(f"full: {raw_title}")
        for kw in raw_title.split():
            if len(kw) > 2:
                raw_keywords.append(f"word: {kw}")

    # Step 5: Manual match check
    keyword_q = Q()
    for opt in all_replace_options:
        raw_title = (opt.title or "").strip()
        keyword_q |= Q(title__icontains=raw_title)
        words = raw_title.split()
        for kw in words:
            if len(kw) > 2:
                keyword_q |= Q(title__icontains=kw)
        for i in range(len(words) - 1):
            compound = words[i] + words[i+1]
            keyword_q |= Q(title__icontains=compound)

    matched_candidates = Product.objects.filter(keyword_q, status="approved").exclude(owner=request.user)
    matched_data = [
        {"id": p.id, "title": p.title, "owner_id": p.owner_id}
        for p in matched_candidates
    ]

    # Step 6: Profile map check
    owner_ids = [c["owner_id"] for c in matched_data]
    profiles = UserProfile.objects.filter(user_id__in=owner_ids)
    profile_map_data = [
        {
            "user_id": p.user_id,
            "lat": str(p.latitude),
            "lng": str(p.longitude),
            "has_location": p.latitude is not None and p.longitude is not None,
        }
        for p in profiles
    ]

    # Step 7: Distance check
    distance_data = []
    owner_lat = float(owner_profile.latitude)
    owner_lng = float(owner_profile.longitude)
    for p in profiles:
        if p.latitude and p.longitude:
            dist = haversine(owner_lat, owner_lng, float(p.latitude), float(p.longitude))
            distance_data.append({"user_id": p.user_id, "dist_km": round(dist, 2)})

    return Response({
        "my_profile":        profile_data,
        "my_products":       my_products_data,
        "all_candidates":    candidates_data,
        "raw_keywords":      raw_keywords,
        "matched_candidates": matched_data,
        "profile_map":       profile_map_data,
        "distances":         distance_data,
    })