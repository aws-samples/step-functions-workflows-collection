from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import StepFunctions, Eventbridge
from diagrams.aws.database import Dynamodb
from diagrams.aws.ml import Bedrock
from diagrams.aws.security import SecretsManager
from diagrams.aws.general import General
from diagrams.saas.chat import Slack

graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.8",
    "nodesep": "1.0",
    "ranksep": "1.2",
}

with Diagram(
    "AWS Feature Relevance Notification System",
    filename="/Users/rahulrsr/Documents/recipe-app/feature-relevance-poc/architecture",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):

    # Input sources
    with Cluster("Input Sources"):
        rss_feed = General("AWS What's New\nRSS Feed\n(~200 posts/month)")
        tam_input = General("TAM / User\n(creates workload\nprofiles)")

    # Scheduling
    with Cluster("Scheduling"):
        scheduler = Eventbridge("EventBridge\nScheduler\n(once per day)")

    # Workload Management
    with Cluster("Workload Management"):
        wl_lambda = Lambda("Workload\nManager\nLambda")
        profiles_table = Dynamodb("Workload\nProfiles\n(DynamoDB)")

    # Ingestion
    with Cluster("Ingestion & Matching"):
        rss_lambda = Lambda("RSS Ingestion\nLambda")
        dedup_table = Dynamodb("Announcement\nState\n(DynamoDB dedup)")

    # Orchestration & AI
    with Cluster("Orchestration & AI Scoring"):
        step_fn = StepFunctions("Step Functions\nPipeline")
        scorer = Lambda("Relevance\nScorer\nLambda")
        bedrock = Bedrock("Amazon Bedrock\nClaude Sonnet 4\n(scoring)")
        kb = Bedrock("Bedrock\nKnowledge Base\n(workload docs)")

    # Notification
    with Cluster("Notification Delivery"):
        notif_lambda = Lambda("Slack\nNotification\nLambda")
        secrets = SecretsManager("Secrets\nManager\n(webhook URL)")
        slack = Slack("Slack Channel")

    # --- Workload Management Flow ---
    tam_input >> Edge(label="invokes\n(CLI / API)", color="gray") >> wl_lambda
    wl_lambda >> Edge(label="stores\nprofile", color="gray") >> profiles_table

    # --- RSS Polling Flow ---
    rss_feed >> Edge(label="fetches", color="darkgreen") >> scheduler
    scheduler >> Edge(label="triggers\nonce/day", color="darkgreen") >> rss_lambda

    # RSS Lambda reads state
    rss_lambda >> Edge(label="dedup\ncheck", color="blue", style="dashed") >> dedup_table
    rss_lambda >> Edge(label="match\nservices", color="blue", style="dashed") >> profiles_table

    # RSS Lambda triggers Step Functions
    rss_lambda >> Edge(label="matched\nannouncement", color="darkgreen", style="bold") >> step_fn

    # --- Scoring Flow ---
    step_fn >> Edge(color="purple") >> scorer
    scorer >> Edge(label="retrieve\ncontext", color="blue", style="dashed") >> kb
    scorer >> Edge(label="score\nrelevance", color="purple", style="bold") >> bedrock

    # --- Notification Flow ---
    step_fn >> Edge(label="score ≥ 40", color="orange", style="bold") >> notif_lambda
    notif_lambda >> Edge(color="blue", style="dashed") >> secrets
    notif_lambda >> Edge(label="enriched\nnotification", color="orange", style="bold") >> slack
