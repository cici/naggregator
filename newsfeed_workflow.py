import coloredlogs
from datetime import timedelta
from logging import getLogger
from news_data import TopicInput, EmailDetails
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from activities import NewsActivities

logger = getLogger(__name__)
coloredlogs.install(level='INFO')


@workflow.defn
class NewsfeedWorkflow:
    def __init__(self) -> None:
        self.email_details = EmailDetails()
        self.sched_to_close_timeout = timedelta(seconds=30)
        self.retry_policy = RetryPolicy(initial_interval=timedelta(seconds=1),
                                        backoff_coefficient=2,
                                        maximum_interval=timedelta(seconds=30),
                                        maximum_attempts=2,
                                        non_retryable_error_types=['TimeoutError', 'ValueError'])
        self._exit: bool = False

    @workflow.run
    async def run(self, topic: TopicInput) -> list:
        logger.info(f"Running Newsfeed Workflow")
        try:
            # while True:
            #     await workflow.wait_condition(
            #         # lambda: not self._pending_request.empty() or self._exit
            #     )
            newsfeed_results = await workflow.execute_activity(NewsActivities.search_news,
                                                               topic,
                                                               schedule_to_close_timeout=self.sched_to_close_timeout,
                                                               retry_policy=self.retry_policy)

            logger.info('OUTPUT')
            # Single entry in newsfeed
            # logger.info(type(newsfeed_results['news_results']))

            await workflow.execute_activity(NewsActivities.notify_slack,
                                            newsfeed_results,
                                            schedule_to_close_timeout=self.sched_to_close_timeout,
                                            retry_policy=self.retry_policy)
        except TimeoutError as te:
            logger.error(f"Timeout Error: {te}")
            raise ApplicationError("Workflow has timed out")
        except ActivityError as ae:
            logger.error(f"Activity has failed with error: {ae}")
            raise ApplicationError("An Activity error has occurred")
        except Exception as err:
            logger.error(f"UNKNOWN EXCEPTION: {err}, {type(err)=}")
            raise ApplicationError("An Unknown Error has occured")

        logger.debug(f"Results passed back from activity")

        if self._exit:
            return "exiting"
        return newsfeed_results


@workflow.signal
def exit(self) -> None:
    self._exit = True


# async def update_schedule_simple(input: ScheduleUpdateInput) -> ScheduleUpdate:
#     schedule_action = input.description.schedule.action

#     if isinstance(schedule_action, ScheduleActionStartWorkflow):
#         schedule_action.args = ["my new schedule arg"]
#     return ScheduleUpdate(schedule=input.description.schedule)

# # Assuming you have a client and a schedule_id
# client = await Client.connect("localhost:7233")
# schedule_handle = client.get_schedule_handle("your-schedule-id")

# await schedule_handle.update(update_schedule_simple)
