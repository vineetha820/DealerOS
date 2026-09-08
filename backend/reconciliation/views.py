from decimal import Decimal

from rest_framework.response import Response
from rest_framework.views import APIView

from reconciliation.comparison import find_disagreements


class DisagreementListView(APIView):
    def get(self, request):
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response({"error": "org_id query parameter is required."}, status=400)

        reason = request.query_params.get("reason")
        sort = request.query_params.get("sort")

        disagreements = find_disagreements()
        disagreements = filter_by_org(disagreements, org_id)

        if reason:
            disagreements = filter_by_reason(disagreements, reason)

        if sort == "value":
            disagreements = sort_by_value(disagreements)

        results = []
        for disagreement in disagreements:
            results.append(format_disagreement(disagreement))

        return Response(
            {
                "count": len(results),
                "results": results,
            }
        )


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
