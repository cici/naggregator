import coloredlogs
from datetime import timedelta
from logging import getLogger
from news_data import NewsfeedInput
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError
from typing import List, Dict
import asyncio
import sys

with workflow.unsafe.imports_passed_through():
    from activities import NewsActivities

logger = getLogger(__name__)
coloredlogs.install(level='INFO')

# Function for generating next date in sequence (for demo purposes)
def getNextDate(today_date):
    # Get current year, month, day from the string
    year, month, day = map(int, today_date.split('-'))
    
    # Increment the day
    day += 1
    
    # Handle month/year rollovers
    days_in_month = {
        1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
    }
    # Simple leap year check
    if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        days_in_month[2] = 29
        
    if day > days_in_month[month]:
        day = 1
        month += 1
        if month > 12:
            month = 1
            year += 1
    
    # Format back to string
    new_date = f"{year}-{month:02d}-{day:02d}"
    logger.info(f"Updated date from {today_date} to {new_date}")
    input.topicDate = new_date
    return new_date

@workflow.defn
class NewsfeedWorkflow:
    def __init__(self) -> None:
        self._email_details = EmailDetails()
        self._start_date = None  # To track when we started collecting results
        self._day_count = 0  # To track how many days we've been running    
        self._sched_to_close_timeout = timedelta(seconds=30)
        self._retry_policy = RetryPolicy(initial_interval=timedelta(seconds=1),
                                        backoff_coefficient=2,
                                        maximum_interval=timedelta(seconds=30),
                                        maximum_attempts=2,
                                        non_retryable_error_types=['Exception'])
        self._newsfeed_result: List[Dict] = []
        self._exit: bool = False
        self._processed_dates: set = set()  # Set to track all the dates we've processed
        self._last_signal_time = None  # To track when we last received a signal

    @workflow.run
    async def run(self, input: NewsfeedInput) -> list:
        """
        Workflow that accumulates results via signals and resets after 7 days.
        
        Args:
            initial_data: Optional data to start with (used in fresh runs)
        
        Returns:
            The accumulated results for the current week
        """
        logger.info(f"Running Newsfeed Workflow")

        # Keep track of all dates we've processed
        self._processed_dates = set()

        # Initialize or restore workflow state from previous runs
        if input.previousResults and len(input.previousResults) > 0:
            self._newsfeed_result = input.previousResults
            logger.info(f"Restored {len(self._newsfeed_result)} previous results")
            
            # Extract dates from existing results to track what dates we've processed
            for article in self._newsfeed_result:
                if 'date' in article:
                    self._processed_dates.add(article['date'])
            
            logger.info(f"Extracted {len(self._processed_dates)} unique dates from previous results: {self._processed_dates}")
        else:
            self._newsfeed_result = []
            logger.info("Starting with empty results")

        # Create a set of existing article identifiers to prevent duplicates
        # We'll use title + link + date as a unique identifier for articles
        # This ensures that the same article on different days is treated as different
        existing_article_ids = set()
        for article in self._newsfeed_result:
            # Create a unique ID using title, link, and date
            article_id = f"{article.get('title', '')}-{article.get('link', '')}-{article.get('date', '')}"
            existing_article_ids.add(article_id)
        
        logger.info(f"Tracking {len(existing_article_ids)} unique articles to prevent duplicates")

        self._day_count += 1
        logger.info(f"This is day {self._day_count} of running this workflow")

        # Main workflow loop - will continue until exit signal is received
        while not self._exit:
            try:
                # Get today's result from an activity (activities CAN use datetime.now())
                today_date = input.topicDate
                logger.info(f"Searching for news on topics: {input.topicString} for date: {today_date}")
                
                # Track this date as processed
                self._processed_dates.add(today_date)
                logger.info(f"Now tracking {len(self._processed_dates)} unique dates: {sorted(list(self._processed_dates))}")
                
                activity_result = await workflow.execute_activity(
                    NewsActivities.search_news,
                    input,
                    schedule_to_close_timeout=self._sched_to_close_timeout,
                    retry_policy=self._retry_policy
                )
                
                logger.info(f"Received activity result of type: {type(activity_result)}")
                
                # Track how many new items we add in this run
                new_items_count = 0
                duplicate_count = 0
                
                # Handle the activity result based on its type
                if isinstance(activity_result, dict):
                    # If it's a dictionary with date keys
                    logger.info(f"Processing dictionary result with {len(activity_result)} date entries")
                    for date_key, news_items in activity_result.items():
                        for idx, item in enumerate(news_items):
                            # Create a dictionary with all the necessary fields
                            news_item = {
                                'position': idx,
                                'title': item.get('title', 'No Title'),
                                'link': item.get('link', '#'),
                                'source': item.get('source', 'Unknown'),
                                'date': date_key,
                                'thumbnail': item.get('thumbnail', ''),
                                'snippet': item.get('snippet', 'No description available')
                            }
                            
                            # Check if this is a duplicate article
                            article_id = f"{news_item['title']}-{news_item['link']}-{news_item['date']}"
                            if article_id in existing_article_ids:
                                duplicate_count += 1
                                continue
                            
                            # Not a duplicate, add to results and tracking set
                            self._newsfeed_result.append(news_item)
                            existing_article_ids.add(article_id)
                            new_items_count += 1
                            
                else:
                    # Unexpected result type
                    logger.warning(f"Unexpected result type from activity: {type(activity_result)}")
                
                # Comment out for now until we are ready to notify results
                await workflow.execute_activity(NewsActivities.notify_slack,
                                                self._newsfeed_result,
                                                schedule_to_close_timeout=self._sched_to_close_timeout,
                                                retry_policy=self._retry_policy)
                logger.info(f"Added {new_items_count} new items for {today_date} (skipped {duplicate_count} duplicates)")
                logger.info(f"Total items across all dates: {len(self._newsfeed_result)}")

                # Check if a continue-as-new is suggested (for workflow history size limitations)
                if workflow.info().is_continue_as_new_suggested():
                    logger.info("Continue-as-new suggested, continuing with current results")
                    workflow.continue_as_new(input, self._newsfeed_result)

                # Sleep for the daily interval (for demo purposes, we'll use 30 seconds)
                logger.info(f"Workflow sleeping before next daily run")
                
                # Use a timeout-protected sleep approach to prevent hanging
                try:
                    logger.info("Beginning sleep cycle with safeguards...")
                    
                    # Instead of a complex sleep loop, use a single sleep with a reasonable timeout
                    logger.info("Starting single 15-second sleep period")
                    sleep_start_time = workflow.now()
                    
                    # Set a shorter timeout to avoid hanging indefinitely
                    try:
                        await asyncio.wait_for(workflow.sleep(15), timeout=35)
                        logger.info("Sleep completed successfully")
                    except asyncio.TimeoutError:
                        logger.error("Sleep operation timed out - forcing continuation")
                    except Exception as e:
                        logger.error(f"Error during sleep: {e}")
                    
                    sleep_duration = (workflow.now() - sleep_start_time).total_seconds()
                    logger.info(f"Actual sleep duration: {sleep_duration:.1f} seconds")
                    
                except Exception as e:
                    logger.error(f"Critical error in sleep handling: {e}")
                    # Continue execution even if sleep fails
                
                # If we've received an exit signal during sleep, break out of the main loop
                if self._exit:
                    logger.info("Exit signal active - breaking out of main workflow loop")
                    break
                
                logger.info("*** WORKFLOW WAKING UP FOR NEXT DAILY RUN ***")
                
                # Update the date for the next run
                next_date = getNextDate(today_date)
                # Also add this to our processed dates tracking
                self._processed_dates.add(next_date)

            except TimeoutError as te:
                logger.error(f"Timeout Error: {te}")
                raise ApplicationError("Workflow has timed out")
            except ActivityError as ae:
                logger.error(f"Activity has failed with error: {ae}")
                raise ApplicationError("An Activity error has occurred")
            except Exception as err:
                logger.error(f"UNKNOWN EXCEPTION: {err}, {type(err)=}")
                raise ApplicationError("An Unknown Error has occured")
        
        logger.info("Workflow exiting due to exit signal")
        return self._newsfeed_result


    @workflow.update
    async def append_result(self, new_result: Dict) -> List[Dict]:
        self._newsfeed_result.append(new_result)
        return self._newsfeed_result

    @workflow.query
    def newsfeed_details(self) -> List[Dict]:
        return self._newsfeed_result
    
    @workflow.query
    def get_current_results(self) -> List[Dict]:
        """Query to get current accumulated results"""
        return self._newsfeed_result

    @workflow.signal
    def exit(self) -> None:
        self._exit = True
        
    @workflow.signal
    def is_running(self) -> None:
        """Signal to ensure the workflow is still running and continues processing.
        This is used to wake up the workflow if it's sleeping and ensure it keeps
        running for subsequent days.
        """
        logger.info("*** RECEIVED IS_RUNNING SIGNAL ***")
        
        # Force logger flush to make sure we see this message immediately
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        
        # Flag that we received a keepalive signal
        self._last_signal_time = workflow.now()
        
    @workflow.query
    def get_processed_dates(self) -> List[str]:
        """Query to get all the dates this workflow has processed."""
        return list(self._processed_dates)
