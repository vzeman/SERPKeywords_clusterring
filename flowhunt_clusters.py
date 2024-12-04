import json

import flowhunt
import streamlit as st
from d3graph import vec2adjmat
from streamlit_d3graph import d3graph


def get_api_client(api_key):
    configuration = flowhunt.Configuration(host="https://api.flowhunt.io", api_key={"APIKeyHeader": api_key})
    return flowhunt.ApiClient(configuration)

def get_groups(api_client, workspace_id):
    api_instance = flowhunt.SERPApi(api_client)
    try:
        return api_instance.search_cluster_group(workspace_id, flowhunt.SerpClusterGroupSearchRequest())
    except Exception:
        return []

def get_group_queries(api_client, workspace_id, group_id):
    api_instance = flowhunt.SERPApi(api_client)
    return api_instance.search_cluster_query(workspace_id=workspace_id, group_id=group_id, serp_cluster_group_search_request=flowhunt.SerpClusterGroupSearchRequest())

def get_intersections(api_client, workspace_id, group_id, group_queries):
    api_instance = flowhunt.SERPApi(api_client)
    source, target, weight = [], [], []
    requests = []

    for q in group_queries:
        requests.append(flowhunt.SerpClusterQueryIntersectionsRequest(query=q.query, group_id=group_id, live_mode=True, max_position=20))
        if len(requests) == 100:
            source, target, weight = process_requests(api_instance, workspace_id, group_id, requests, source, target, weight)
            requests = []

    if requests:
        source, target, weight = process_requests(api_instance, workspace_id, group_id, requests, source, target, weight)

    return source, target, weight

def process_requests(api_instance, workspace_id, group_id, requests, source, target, weight):
    results = api_instance.serp_cluster_get_bulk_query_intersections(workspace_id=workspace_id, serp_cluster_query_intersections_request=requests)
    for i, r in enumerate(results):
        if r.status == "SUCCESS":
            intersections = json.loads(r.result)
            for g in intersections:
                if g["group_id"] == group_id:
                    for query in g["queries"]:
                        source.append(requests[i].query)
                        target.append(query["query"])
                        weight.append(query["count"])
    return source, target, weight

st.set_page_config(layout="wide", initial_sidebar_state="expanded")
with st.sidebar:
    api_key = st.text_input(label="FlowHunt API Key")

if api_key and len(api_key) == 36:
    with get_api_client(api_key) as api_client:
        current_user = flowhunt.AuthApi(api_client).get_user()
        workspace_id = current_user.api_key_workspace_id
        groups = get_groups(api_client, workspace_id)

    with st.sidebar:
        selected_group = st.selectbox(label="select group id", options=[group.group_name for group in groups], index=None)

    if selected_group:
        group_id = next(group.group_id for group in groups if group.group_name == selected_group)
        with get_api_client(api_key) as api_client:
            group_queries = get_group_queries(api_client, workspace_id, group_id)
            source, target, weight = get_intersections(api_client, workspace_id, group_id, group_queries)

        adjmat = vec2adjmat(source, target, weight=weight)
        d3 = d3graph()
        d3.graph(adjmat)
        d3.show(figsize=(1500, 1500), title="Keyword Cluster for " + selected_group)