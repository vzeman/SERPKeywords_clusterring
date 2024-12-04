import streamlit as st
from d3graph import vec2adjmat
from streamlit_d3graph import d3graph

import flowhunt
import json

source = []
target = []
weight = []

with st.sidebar:
    api_key = st.text_input(label="FlowHunt API Key")

if api_key and len(api_key) == 36:
    # Configure Bearer authorization: HTTPBearer
    configuration = flowhunt.Configuration(host = "https://api.flowhunt.io",
                                           api_key = {"APIKeyHeader": api_key})

    # Enter a context with an instance of the API client
    with flowhunt.ApiClient(configuration) as api_client:
        # Create an instance of the API class
        api_instance = flowhunt.AuthApi(api_client)
        current_user = api_instance.get_user()
    workspace_id = current_user.api_key_workspace_id
    with flowhunt.ApiClient(configuration) as api_client:
        api_instance = flowhunt.SERPApi(api_client)
        try:
            # Search Cluster Group
            groups = api_instance.search_cluster_group(workspace_id, flowhunt.SerpClusterGroupSearchRequest())
        except Exception as e:
            pass
            #print("Exception when calling SERPApi->search_cluster_group: %s\n" % e)
    with st.sidebar:
        selected_group = st.selectbox(
            label="select group id",
            options=[group.group_name for group in groups],
            index=None
        )

    if selected_group:
        group_id = [group.group_id for group in groups if group.group_name == selected_group][0]
        group_queries = api_instance.search_cluster_query(workspace_id=workspace_id, group_id= group_id, serp_cluster_group_search_request=flowhunt.SerpClusterGroupSearchRequest())

        for q in group_queries:
            q_intersections = api_instance.serp_cluster_get_query_intersections(workspace_id=workspace_id, serp_cluster_query_intersections_request=flowhunt.SerpClusterQueryIntersectionsRequest(query=q.query, group_id=group_id, live_mode=True, max_position=20))
            if q_intersections.status == "SUCCESS":
                intersections = json.loads(q_intersections.result)
                for g in intersections:
                    if g["group_id"] == group_id:
                        for i in g["queries"]:
                            source.append(q.query)
                            target.append(i["query"])
                            weight.append(i["count"])

        adjmat = vec2adjmat(source, target, weight=weight)

        # Initialize
        d3 = d3graph()
        d3.graph(adjmat)
        d3.show()

