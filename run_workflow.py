import asyncio
import coloredlogs
import logging
import os
from newsfeed_workflow import NewsfeedWorkflow
from news_data import Topic
from temporal_client import NewTemporalClient

# Create a logger object and use coloredlogs
logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG')

# Get the task queue name from the environment variable
NEWS_TASK_QUEUE = os.environ.get("NEWS_TASK_QUEUE", "NewsTaskQueue")
NEWS_TOPIC = os.environ.get("NEWS_TOPIC", "bitoin Apple OpenAI")
NEWS_DATE = os.environ.get("NEWS_DATE", "December 8, 2024")


async def main() -> None:
    # Start client
    client = await NewTemporalClient()

    # If form input is null, get topics from ENV
    topics = NEWS_TOPIC.split(",")
    topic = Topic(NEWS_DATE, topics)

    newsfeed_handle = await client.start_workflow(
        NewsfeedWorkflow.run,
        topic,
        id="newsfeed-workflow",
        task_queue=NEWS_TASK_QUEUE,
    )

    # Wait for the workflow to complete and get the result
    result = await newsfeed_handle.result()

    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
