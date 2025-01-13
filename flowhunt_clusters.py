import json
import flowhunt
import streamlit as st
from d3graph import vec2adjmat
from streamlit_d3graph import d3graph
from st_material_table import st_material_table
import pandas as pd


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

def get_intersections(api_client, workspace_id, group_id, group_queries, graph_placeholder):
    api_instance = flowhunt.SERPApi(api_client)
    source, target, weight = [], [], []
    requests = []

    progress_bar = st.progress(0)
    total_queries = len(group_queries)
    d3 = d3graph()

    for idx, q in enumerate(group_queries):
        requests.append(flowhunt.SerpClusterQueryIntersectionsRequest(query=q.query, group_id=group_id, live_mode=True, max_position=20))
        if len(requests) == 50:
            source, target, weight = process_requests(api_instance, workspace_id, group_id, requests, source, target, weight)
            requests = []
            adjmat = vec2adjmat(source=source, target=target, weight=weight)
            d3.graph(adjmat)
            with graph_placeholder:
                d3.show(figsize=(1000, 600), title="Keyword Cluster for " + selected_group)
            progress_bar.progress((idx + 1) / total_queries)

    if len(requests) > 0:
        source, target, weight = process_requests(api_instance, workspace_id, group_id, requests, source, target, weight)
        adjmat = vec2adjmat(source=source, target=target, weight=weight)
        d3.graph(adjmat)
        with graph_placeholder:
            d3.show(figsize=(1000, 600), title="Keyword Cluster for " + selected_group)
        progress_bar.progress(1.0)

    return source, target, weight

def process_requests(api_instance, workspace_id, group_id, requests, source, target, weight):
    try:
        results = api_instance.serp_cluster_get_bulk_query_intersections(workspace_id=workspace_id, serp_cluster_query_intersections_request=requests)
        for i, r in enumerate(results):
            if r.status == "SUCCESS":
                intersections = json.loads(r.result)
                for g in intersections:
                    if g["group_id"] == group_id:
                        for query in g["queries"]:
                            if requests[i].query != query["query"]:
                                source.append(requests[i].query)
                                target.append(query["query"])
                                weight.append(query["count"])
    except Exception:
        pass
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
            tab1, tab2 = st.tabs(["Queries Table", "Graph of relationships"])

            display_df = pd.DataFrame([q.query for q in group_queries])
            with tab1:
                _ = st_material_table(display_df)

            with tab2:
                with st.spinner("Computing intersections..."):
                    graph_placeholder = st.empty()
                    source, target, weight = get_intersections(api_client, workspace_id, group_id, group_queries, graph_placeholder)

# Add custom CSS and JavaScript for borders and responsive graph
st.markdown(
    """
    <style>
    .stTabs [role="tablist"] {
        border: 2px solid #ccc;
        padding: 10px;
        border-radius: 5px;
    }
    .stTabs [role="tabpanel"] {
        border: 2px solid #ccc;
        padding: 10px;
        border-radius: 5px;
        height: 70vh; /* Set height to 70% of the viewport height */
    }
    .stGraph {
        border: 2px solid #ccc;
        padding: 10px;
        border-radius: 5px;
    }
    .stGraph > div {
        width: 100% !important;
        height: 100% !important;
    }
    </style>
    <script>
    function setTabHeight() {
        const tabPanels = document.querySelectorAll('.stTabs [role="tabpanel"]');
        tabPanels.forEach(panel => {
            panel.style.height = (window.innerHeight * 0.7) + 'px';
        });
    }
    window.addEventListener('resize', setTabHeight);
    window.addEventListener('load', setTabHeight);
    </script>
    """,
    unsafe_allow_html=True
)