import asyncio
import coloredlogs
import logging
from dotenv import load_dotenv
from temporal_client import NewTemporalClient
from temporalio.worker import Worker
from newsfeed_workflow import NewsfeedWorkflow
from activities import NewsActivities
from news_data import NEWS_TASK_QUEUE
import concurrent.futures

load_dotenv()

interrupt_event = asyncio.Event()


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

    # Setup schedule for daily execution
    # await client.create_schedule(
    #     "daily-result-accumulator",
    #     client.schedule_client.Schedule(
    #         action=client.schedule_client.Schedule.Action(
    #             start_workflow=client.schedule_client.Schedule.Action.StartWorkflow(
    #                 workflow="NewsfeedWorkflow",
    #                 id="weekly-news-workflow",
    #                 task_queue=NEWS_TASK_QUEUE,
    #             )
    #         ),
    #         spec=client.schedule_client.ScheduleSpec(
    #             cron_expressions=["0 0 * * *"]  # Daily at midnight
    #         )
    #     )
    # )

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    coloredlogs.install(level='INFO')
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
    # asyncio.run(main())
