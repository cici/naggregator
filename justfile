# NOTE: If environment variables aren't being picked up from .env, run this first:
# unset NEWS_TASK_QUEUE SERPAPI_KEY TEMPORAL_CLI_NAMESPACE TEMPORAL_CLI_ADDRESS TEMPORAL_MTLS_TLS_KEY TEMPORAL_MTLS_TLS_CERT

set dotenv-required := true
set dotenv-load := true

# NOTE: run_web is used if you want to execute via the Web UI and it replaces the need to use run_workflow
run_web:
    @echo "To use the .env file, first unset TEMPORAL_TASK_QUEUE TEMPORAL_CONNECTION_NAMESPACE TEMPORAL_CONNECTION_TARGET TEMPORAL_CONNECTION_MTLS_KEY_FILE TEMPORAL_CONNECTION_MTLS_CERT_CHAIN_FILE TEMPORAL_CONNECTION_WEB_PORT CALLER_API_PORT PUBLIC_WEB_URL"
    @echo "Starting web at $PUBLIC_WEB_URL"
    poetry run python run_web.py

run_worker:
  python run_worker.py

# NOTE: run_workflow is used for scheduling and replaces the need to use run_web
run_workflow:
  python run_workflow.py

