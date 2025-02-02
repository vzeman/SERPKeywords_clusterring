import flowhunt
import flowhunt
import networkx as nx
import pandas as pd
import streamlit as st
from community import community_louvain
from d3graph import vec2adjmat, adjmat2vec
from st_material_table import st_material_table
from streamlit_d3graph import d3graph


def get_api_client(api_key):
    #configuration = flowhunt.Configuration(host="http://localhost:9010", api_key={"APIKeyHeader": api_key})
    configuration = flowhunt.Configuration(host="https://api.flowhunt.io", api_key={"APIKeyHeader": api_key})
    return flowhunt.ApiClient(configuration)

def get_customers(api_client, workspace_id):
    api_instance = flowhunt.GoogleAdsApi(api_client)
    try:
        return api_instance.get_google_ads_customers(workspace_id)
    except Exception:
        return None

def get_campaigns(api_client, workspace_id, customer_id):
    api_instance = flowhunt.GoogleAdsApi(api_client)
    try:
        return api_instance.get_google_ads_campaigns(customer_id, workspace_id)
    except Exception:
        return None

def get_groups(api_client, workspace_id, customer_id, campaign_id):
    api_instance = flowhunt.GoogleAdsApi(api_client)
    try:
        return api_instance.get_google_ads_groups(customer_id, campaign_id, workspace_id)
    except Exception:
        return None

def get_group_queries(api_client, workspace_id, customer_id, campaign_id, group_id):
    api_instance = flowhunt.SERPApi(api_client)
    serp_cluster_group_search_request = flowhunt.SerpClusterGroupSearchRequest(
        customer_id=customer_id,
        campaign_id=campaign_id,
        group_id=group_id,
    )
    try:
        return api_instance.search_cluster_query(workspace_id, serp_cluster_group_search_request)
    except Exception:
        return None


def get_intersections(api_client, workspace_id, customer_id, campaign_id, group_id, group_queries):
    api_instance = flowhunt.SERPApi(api_client)
    source =  [q.keyword for q in group_queries]
    target =  [q.keyword for q in group_queries]
    weight = [20 for q in group_queries]


    serp_cluster_group_intersections_request = flowhunt.SerpClusterGroupIntersectionsRequest(
        customer_id=customer_id,
        campaign_id=campaign_id,
        group_id=group_id,
        min_cluster_strength=3,
        suggest_other_matching_keywords=True
    )

    try:
        intersection = api_instance.serp_cluster_get_graph_nodes(workspace_id=workspace_id, serp_cluster_group_intersections_request=serp_cluster_group_intersections_request)
        for i in intersection:
            source.append(i.keyword_1)
            target.append(i.keyword_2)
            weight.append(i.count)
    except Exception as e:
        pass

    return vec2adjmat(source=source, target=target, weight=weight)


st.set_page_config(layout="wide", initial_sidebar_state="expanded")
with st.sidebar:
    api_key = st.text_input(label="FlowHunt API Key")

customer_id=None
campaign_id=None
group_id=None
group_keywords=[]

if api_key and len(api_key) == 36:
    with get_api_client(api_key) as api_client:
        current_user = flowhunt.AuthApi(api_client).get_user()
        workspace_id = current_user.api_key_workspace_id
        customers = get_customers(api_client, workspace_id)

    with st.sidebar:
        selected_customer = st.selectbox(label="select customer", options=[customer.customer_name for customer in customers.customers], index=None)

    if selected_customer:
        customer_id = next(customer.customer_id for customer in customers.customers if customer.customer_name == selected_customer)

    if customer_id:

        with get_api_client(api_key) as api_client:
            campaigns = get_campaigns(api_client, workspace_id, customer_id)

        with st.sidebar:
            selected_campaign = st.selectbox(label="select campaign", options=[campaign.campaign_name for campaign in campaigns.campaigns], index=None)

        if selected_campaign:
            campaign_id = next(campaign.campaign_id for campaign in campaigns.campaigns if campaign.campaign_name == selected_campaign)

        if campaign_id:
            with get_api_client(api_key) as api_client:
                groups = get_groups(api_client, workspace_id, customer_id, campaign_id)

            with st.sidebar:
                selected_group = st.selectbox(label="select group", options=[group.group_name for group in groups.groups], index=None)

            if selected_group:
                group_id = next(group.group_id for group in groups.groups if group.group_name == selected_group)

    if customer_id or campaign_id or group_id:
        with get_api_client(api_key) as api_client:
            group_queries = get_group_queries(api_client, workspace_id, customer_id, campaign_id, group_id)
            tab2, tab3 = st.tabs(["Graph of relationships", "Keyword Clusters"])

            display_df = pd.DataFrame([q.keyword for q in group_queries])
            group_keywords = [q.keyword for q in group_queries]

            adjmat = get_intersections(api_client=api_client,
                                       workspace_id=workspace_id,
                                       customer_id=customer_id,
                                       campaign_id=campaign_id,
                                       group_id=group_id,
                                       group_queries=group_queries)

            with tab2:
                with st.spinner("Computing intersections..."):
                    graph_placeholder = st.empty()
                    d3 = d3graph()
                    d3.graph(adjmat)
                    with graph_placeholder:
                        d3.show(figsize=(1000, 600), title="Keyword Cluster", save_button=False)


            with tab3:
                with st.spinner("Computing clusters..."):
                    df = adjmat2vec(adjmat)
                    G = nx.from_pandas_edgelist(df, edge_attr=True, create_using=nx.MultiGraph)
                    # Partition
                    G = G.to_undirected()
                    cluster_labels = community_louvain.best_partition(G, weight='weight')
                    clusters = {}
                    for i, key in enumerate(cluster_labels.keys()):
                        label = cluster_labels.get(key)
                        if label in clusters:
                            clusters[label] += "\n[" + key + "]"
                        else:
                            clusters[label] = "["+ key + "]"
                    display_df = pd.DataFrame(clusters.values())
                    _ = st_material_table(display_df)


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