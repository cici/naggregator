import asyncio
import coloredlogs
import logging
import os
import serpapi
from logging import getLogger
from temporalio import activity
from news_data import Topic


NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# Create a logger object
logger = getLogger(__name__)
# Install coloredlogs
coloredlogs.install(level='DEBUG')


class NewsActivities:

    @activity.defn
    async def fetch_news(activity_input: Topic) -> list[str]:
        """Function retrieves the news based on input"""

        logger.debug("From fetch news")
        client = serpapi.Client(api_key=NEWS_API_KEY)

        # result = client.search(
        #     q="coffee",
        #     engine="google",
        #     location="Austin, Texas",
        #     hl="en",
        #     gl="us",
        # )

        print("END OF ACTIVITY")

    @activity.defn
    def fetch_news2(activity_input: Topic) -> dict:
        """Function retrieves the news based on the prompt"""

        logger.info("Fetching the news")

        # Define the prompt and configuration
        delimiter = ','
        topicStr = delimiter.join(map(repr, activity_input.topicList))
        PROMPT = "I want to see the latest tech news articles, including links to each article, on {topics} since {topic_date}. \
        Please include sites like techcrunch.com, wired.com, cnet.com and technewsworld.com in the search. \
        The result needs to be in JSON format without a parent level node and include the source of the article, the URL to the article, \
        the title of the article and the date it was published.".format(topics=topicStr, topic_date=activity_input.topicDate)

        graph_config = {
            "llm": {
                "api_key": CLAUDE_KEY,
                "model": "anthropic/claude-3-haiku-20240307",
            },
            "max_results": 4,
            "verbose": True,
        }

        # Create and run the search graph
        # LEAVE THIS COMMENTED OUT FOR NOW
        # DON'T WASTE SEARCH CREDITS
        # READ IN PREVIOUS SEARCH RESULTS FROM JSON FILE
        print(PROMPT)
        # try:
        #     search_graph = SearchGraph(
        #         prompt=PROMPT, config=graph_config)
        #     results = search_graph.run()
        # except ActivityError as e:
        #     if isinstance(e.cause, ApplicationError):
        #         app_error = e.cause
        #         print(f"An ApplicationError occurred in the activity: {
        #               app_error}")

        with open('results.json', 'r') as f:
            results = json.load(f)

        print(results)

        # graph_exec_info = search_graph.get_execution_info()
        # print(prettify_exec_info(graph_exec_info))

        # print(json.dumps(results, indent=4))
        # export_to_json(results, "results.json")

        logger.info("Completed fetching of news")

        return results
