import asyncio
import coloredlogs
import logging
from temporal_client import NewTemporalClient
from temporalio.worker import Worker
from newsfeed_workflow import NewsfeedWorkflow
from activities import NewsActivities
from news_data import NEWS_TASK_QUEUE
import concurrent.futures

logger = logging.getLogger(__name__)
coloredlogs.install(level='INFO')


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s")
    # Start client
    client = await NewTemporalClient()

    # Run a worker for the workflow
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as activity_executor:
        worker = Worker(
            client,
            task_queue=NEWS_TASK_QUEUE,
            workflows=[NewsfeedWorkflow],
            activities=[NewsActivities.search_news,
                        NewsActivities.notify_slack],
            activity_executor=activity_executor,
        )
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
