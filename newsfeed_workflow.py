import coloredlogs
from datetime import timedelta
from logging import getLogger
from news_data import TopicInput, Article, EmailDetails
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError
from typing import List, Dict, Any
import asyncio

with workflow.unsafe.imports_passed_through():
    from activities import NewsActivities

logger = getLogger(__name__)
coloredlogs.install(level='INFO')


@workflow.defn
class NewsfeedWorkflow:
    def __init__(self) -> None:
        self.email_details = EmailDetails()
        self.start_date = None  # To track when we started collecting results
        self.current_day_count = 0  # To track how many days we've been running
        self.sched_to_close_timeout = timedelta(seconds=30)
        self.retry_policy = RetryPolicy(initial_interval=timedelta(seconds=1),
                                        backoff_coefficient=2,
                                        maximum_interval=timedelta(seconds=30),
                                        maximum_attempts=2,
                                        non_retryable_error_types=['TimeoutError', 'ValueError'])
        self._newsfeed: List[Dict] = []
        self._exit: bool = False

    @workflow.run
    async def run(self, topic: TopicInput, initial_data: Any) -> list:
        logger.info(f"Running Newsfeed Workflow")
        # Initialize our workflow state for first execution
        if self.current_day_count == 0 and initial_data is not None:
            self.results.append(initial_data)

        self.day_count += 1

        # Get today's result from an activity (activities CAN use datetime.now())
        today_result = await workflow.execute_activity(
            get_daily_result,
            sched_to_close_timeout=self.sched_to_close_timeout,
            retry_policy=self.retry_policy
        )
        try:
            while True:
                await workflow.wait_condition(
                    lambda: workflow.all_handlers_finished() and not self._newsfeed or self._exit
                )
                newsfeed_results = await workflow.execute_activity(NewsActivities.search_news,
                                                                   topic,
                                                                   schedule_to_close_timeout=self.sched_to_close_timeout,
                                                                   retry_policy=self.retry_policy)

                self._newsfeed = newsfeed_results
                # Single entry in newsfeed
                # logger.info(type(newsfeed_results['news_results']))

                # await workflow.execute_activity(NewsActivities.notify_slack,
                #                                 newsfeed_results,
                #                                 schedule_to_close_timeout=self.sched_to_close_timeout,
                #                                 retry_policy=self.retry_policy)

                if workflow.info().is_continue_as_new_suggested():
                    workflow.continue_as_new()

                await asyncio.sleep(120)  # Wait 2 minutes

        except TimeoutError as te:
            logger.error(f"Timeout Error: {te}")
            raise ApplicationError("Workflow has timed out")
        except ActivityError as ae:
            logger.error(f"Activity has failed with error: {ae}")
            raise ApplicationError("An Activity error has occurred")
        except Exception as err:
            logger.error(f"UNKNOWN EXCEPTION: {err}, {type(err)=}")
            raise ApplicationError("An Unknown Error has occured")

    @workflow.update
    async def append_result(self, new_result: Article) -> list:
        self._newsfeed.append(new_result)
        return self._newsfeed

    @workflow.query
    def newsfeed_details(self):
        return self._newsfeed

    @workflow.signal
    def exit(self) -> None:
        self._exit = True
