# EKS Deployment Manifests

These manifests deploy the MCP-enabled travel planner as two Kubernetes services:

- `travel-langgraph-agent`: internal FastAPI + LangGraph backend.
- `travel-mcp-server`: public MCP Streamable HTTP adapter exposed at `/mcp`.

## Prerequisites

- EKS cluster is running.
- NGINX Ingress Controller is installed.
- Metrics Server is installed if you use the HPA manifest.
- Backend and MCP server images are pushed to ECR.
- Worker nodes can pull from ECR.
- Postgres/Neon database is reachable from the cluster.

## Files

```text
00-namespace.yaml
01-configmap.yaml
02-secret.example.yaml
03-langgraph-agent.yaml
04-mcp-server.yaml
05-ingress.yaml
06-hpa.yaml
kustomization.yaml
```

## Setup

1. Update image URIs in:

```bash
k8s/03-langgraph-agent.yaml
k8s/04-mcp-server.yaml
```

Replace:

```text
111122223333.dkr.ecr.us-east-1.amazonaws.com/...
```

2. Create the runtime secret locally:

```bash
cp k8s/02-secret.example.yaml k8s/02-secret.yaml
```

Then fill:

```text
OPENAI_API_KEY
SERPAPI_API_KEY
DUFFEL_ACCESS_TOKEN
LANGGRAPH_POSTGRES_URI
```

`k8s/02-secret.yaml` is ignored by git.

3. If you have a real DNS name, add a `host` field and TLS settings in:

```bash
k8s/05-ingress.yaml
```

By default the ingress is hostless so temporary HTTPS tunnels, generated hostnames, and direct load balancer tests can route to `/mcp`.

4. For first deployment only, enable table setup in `01-configmap.yaml`:

```text
LANGGRAPH_POSTGRES_SETUP: "true"
BOOKINGS_TABLE_SETUP: "true"
```

For setup, keep `travel-langgraph-agent` replicas at `1` in `03-langgraph-agent.yaml` to avoid multiple pods trying to run migrations at the same time.

Deploy once, confirm startup succeeds, then set both setup flags back to:

```text
LANGGRAPH_POSTGRES_SETUP: "false"
BOOKINGS_TABLE_SETUP: "false"
```

## Deploy

```bash
kubectl apply -k k8s
```

This creates the standalone namespace:

```text
travel-mcp
```

## GitHub Actions

Two repo-level workflows support this project:

- `.github/workflows/build-travel-mcp-images.yml` builds Docker images for `langgraph-agent` and `travel-mcp-server`, pushes them to ECR on `master`, and does build-only validation on pull requests.
- `.github/workflows/deploy-travel-mcp-eks.yml` builds and pushes both images, renders these manifests, applies the runtime secret, deploys to EKS, and waits for rollout.

Required GitHub secrets:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
EKS_CLUSTER_NAME
OPENAI_API_KEY
SERPAPI_API_KEY
DUFFEL_ACCESS_TOKEN
LANGGRAPH_POSTGRES_URI
```

Manual run inputs:

```text
image_tag
ingress_host
run_schema_setup
```

Check resources:

```bash
kubectl get pods -n travel-mcp
kubectl get svc -n travel-mcp
kubectl get ingress -n travel-mcp
```

Connect Claude or another MCP client to:

```text
https://<your-https-host>/mcp
```

Claude Code example:

```bash
claude mcp add --transport http travel-booking https://<your-https-host>/mcp
```

View logs:

```bash
kubectl logs -n travel-mcp deploy/travel-langgraph-agent
kubectl logs -n travel-mcp deploy/travel-mcp-server
```

## Production Notes

- Add authentication or network restrictions between `travel-mcp-server` and `travel-langgraph-agent`.
- Use TLS on the ingress before connecting external MCP clients.
- Replace raw Kubernetes Secret YAML with AWS Secrets Manager, External Secrets Operator, Secrets Store CSI Driver, or Sealed Secrets.
- Add NetworkPolicies so only the MCP server can reach the backend API.
