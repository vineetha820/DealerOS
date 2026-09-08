from decimal import Decimal

from rest_framework.response import Response
from rest_framework.views import APIView

from reconciliation.comparison import find_disagreements


class DisagreementListView(APIView):
    def get(self, request):
        reason = request.query_params.get("reason")
        sort = request.query_params.get("sort")

        disagreements = find_disagreements()

        if reason:
            filtered_disagreements = []
            for disagreement in disagreements:
                if disagreement.reason == reason:
                    filtered_disagreements.append(disagreement)
            disagreements = filtered_disagreements

        if sort == "value":
            disagreements = sorted(disagreements, key=get_value_for_sorting)

        results = []
        for disagreement in disagreements:
            results.append(disagreement_to_dict(disagreement))

        return Response(
            {
                "count": len(results),
                "results": results,
            }
        )


def get_value_for_sorting(disagreement):
    if disagreement.a_value is not None:
        return disagreement.a_value

    for value in disagreement.b_values:
        if value is not None:
            return value

    return Decimal("0")


def disagreement_to_dict(disagreement):
    b_values = []
    for value in disagreement.b_values:
        if value is None:
            b_values.append(None)
        else:
            b_values.append(str(value))

    a_value = None
    if disagreement.a_value is not None:
        a_value = str(disagreement.a_value)

    return {
        "reason": disagreement.reason,
        "org_id": disagreement.org_id,
        "record_id": disagreement.record_id,
        "location_id": disagreement.location_id,
        "location_name": disagreement.location_name,
        "a_value": a_value,
        "b_values": b_values,
        "b_entry_ids": list(disagreement.b_entry_ids),
        "message": disagreement.message,
    }
