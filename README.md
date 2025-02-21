# Python NewsFeed Aggregator
The purpose of this demo is to show how [Temporal](https://temporal.io/) can be used to create a realish-time news feed for specific topics and aggregate the results into a single newsfeed. Several years ago, AWS did a [newsfeed example](https://aws.amazon.com/blogs/architecture/field-notes-building-a-scalable-real-time-newsfeed-watchlist-using-amazon-comprehend/) using all AWS infrastructure and I thought it would be a cool experiment to replicate this (somewhat) and use Temporal.

## Prerequisites
This application uses [Serp API](https://serpapi.com/) to do the searches, so you will need an API Key.

The requirements will be similar (yet more modern) to those in the AWS solution since the ultimate goal is to compare and contrast the architecture at the end.

1. In the AWS solution, a "watchlist" was pre-defined and kept in a data store. In this example, the list will be sent with the request.
2. The AWS solution scraped webpages to find matches. In this example, we will simply use the Google Search SerpAPI to find the relevant matches.
3. Grab RSS feeds based on the created watchlist and put in JSON file
4. Put JSON files in AWS S3 bucket
5. 

### Running the Scenarios
Before running any `just` commands, ensure your environment is clean by unsetting any existing Temporal environment variables:

```bash
unset TEMPORAL_TASK_QUEUE TEMPORAL_CONNECTION_NAMESPACE TEMPORAL_CONNECTION_TARGET TEMPORAL_CONNECTION_MTLS_KEY_FILE TEMPORAL_CONNECTION_MTLS_CERT_CHAIN_FILE TEMPORAL_CONNECTION_WEB_PORT CALLER_API_PORT PUBLIC_WEB_URL
```

# Setup
This demo uses the `just` CLI command runner to easily start the web server and the Temporal Worker
```bash
$ brew install just
```
It also uses Poetry for dependency management and packaging
```bash
$ curl -sSL https://install.python-poetry.org | python3 -
$ poetry install/update (if installed)
```

# Run Web App
```bash
$ just run_web
```

# Run Worker
```bash
$ export SERP_API_KEY=mykey
$ just run_worker
```