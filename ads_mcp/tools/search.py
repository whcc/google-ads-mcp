# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for exposing the API Search method to the MCP server."""

import json
from typing import Any, Dict, List, Optional
from ads_mcp.coordinator import mcp
import ads_mcp.utils as utils


@mcp.tool()
def get_resource_fields(resource: Optional[str] = None) -> list | dict:
    """Returns field metadata for a Google Ads API resource.

    Args:
        resource: The resource name to look up (e.g. "campaign", "ad_group").
                  If omitted, returns a list of all available resource names.
    """
    with open(utils.get_gaql_resources_filepath(), "r") as f:
        resources = json.load(f)

    if resource is None:
        return [r["resource"] for r in resources]

    for r in resources:
        if r["resource"] == resource:
            return r

    return {
        "error": f"Unknown resource '{resource}'. "
        "Call with no arguments to list all resources."
    }


def search(
    customer_id: str,
    fields: List[str],
    resource: str,
    conditions: List[str] = None,
    orderings: List[str] = None,
    limit: int | str = None,
) -> List[Dict[str, Any]]:
    """Fetches data from the Google Ads API using the search method

    Args:
        customer_id: The id of the customer
        fields: The fields to fetch
        resource: The resource to return fields from
        conditions: List of conditions to filter the data, combined using AND clauses
        orderings: How the data is ordered
        limit: The maximum number of rows to return

    """

    ga_service = utils.get_googleads_service("GoogleAdsService")

    query_parts = [f"SELECT {','.join(fields)} FROM {resource}"]

    if conditions:
        query_parts.append(f" WHERE {' AND '.join(conditions)}")

    if orderings:
        query_parts.append(f" ORDER BY {','.join(orderings)}")

    if limit:
        query_parts.append(f" LIMIT {limit}")

    query = "".join(query_parts)
    utils.logger.info(f"ads_mcp.search query {query}")

    query_result = ga_service.search_stream(
        customer_id=customer_id, query=query
    )

    final_output: List = []
    for batch in query_result:
        for row in batch.results:
            final_output.append(
                utils.format_output_row(row, batch.field_mask.paths)
            )
    return final_output


_SEARCH_DESCRIPTION = """\
Fetches data from the Google Ads API using GAQL (Google Ads Query Language).

Constructs: SELECT fields FROM resource [WHERE conditions] [ORDER BY orderings] [LIMIT n]

### Rules
- customer_id: string of digits only, no hyphens (e.g. "1234567890" not "123-456-7890")
- Dates: YYYY-MM-DD format with dashes. Never use GAQL date literals.
- Date ranges must be finite with both a start and end date.
- change_event queries must have LIMIT <= 10000
- All field names must be fully qualified (e.g. "campaign.name", not "name"). No wildcards.
- For conversion issues, try the offline_conversion_upload_conversion_action_summary resource.

### Finding valid fields
Call get_resource_fields with a resource name to discover its selectable, filterable, and sortable fields.

### References
- GAQL grammar: https://developers.google.com/google-ads/api/docs/query/grammar
- All resources: https://developers.google.com/google-ads/api/fields/v21/overview
- Conversion summaries: https://developers.google.com/google-ads/api/docs/conversions/upload-summaries
"""

mcp.add_tool(
    search,
    title="Fetches data from the Google Ads API using the search method",
    description=_SEARCH_DESCRIPTION,
)
