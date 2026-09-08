from decimal import Decimal

from rest_framework.response import Response
from rest_framework.views import APIView

from reconciliation.comparison import find_disagreements


DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50


class DisagreementListView(APIView):
    def get(self, request):
        org_id = request.query_params.get("org_id")
        reason = request.query_params.get("reason")
        sort = request.query_params.get("sort")
        page = get_positive_int(request.query_params.get("page"), 1)
        page_size = get_positive_int(request.query_params.get("page_size"), DEFAULT_PAGE_SIZE)
        if page_size > MAX_PAGE_SIZE:
            page_size = MAX_PAGE_SIZE

        disagreements = find_disagreements()

        if org_id:
            disagreements = filter_by_org(disagreements, org_id)

        if reason:
            disagreements = filter_by_reason(disagreements, reason)

        if sort == "value":
            disagreements = sort_by_value(disagreements)

        total_count = len(disagreements)
        paginated_disagreements = paginate(disagreements, page, page_size)

        results = []
        for disagreement in paginated_disagreements:
            results.append(format_disagreement(disagreement))

        return Response(
            {
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": get_total_pages(total_count, page_size),
                "results": results,
            }
        )


def get_positive_int(value, default):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default

    if number < 1:
        return default

    return number


def get_total_pages(total_count, page_size):
    if total_count == 0:
        return 1

    full_pages = total_count // page_size
    has_partial_page = total_count % page_size > 0
    if has_partial_page:
        return full_pages + 1

    return full_pages


def paginate(disagreements, page, page_size):
    start = (page - 1) * page_size
    end = start + page_size
    return disagreements[start:end]


def filter_by_org(disagreements, org_id):
    filtered = []
    for disagreement in disagreements:
        if disagreement.org_id == org_id:
            filtered.append(disagreement)
    return filtered


def filter_by_reason(disagreements, reason):
    filtered = []
    for disagreement in disagreements:
        if disagreement.reason == reason:
            filtered.append(disagreement)
    return filtered


def sort_by_value(disagreements):
    return sorted(disagreements, key=value_for_sorting)


def value_for_sorting(disagreement):
    if disagreement.a_value is not None:
        return disagreement.a_value

    for value in disagreement.b_values:
        if value is not None:
            return value

    return Decimal("0")


def format_disagreement(disagreement):
    return {
        "reason": disagreement.reason,
        "org_id": disagreement.org_id,
        "record_id": disagreement.record_id,
        "location_id": disagreement.location_id,
        "location_name": disagreement.location_name,
        "a_value": format_amount(disagreement.a_value),
        "b_values": format_amounts(disagreement.b_values),
        "b_entry_ids": list(disagreement.b_entry_ids),
        "message": disagreement.message,
    }


def format_amounts(values):
    formatted_values = []
    for value in values:
        formatted_values.append(format_amount(value))
    return formatted_values


def format_amount(value):
    if value is None:
        return None
    return str(value)
