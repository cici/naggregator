import os
from dataclasses import dataclass, field
from typing import List, Dict
NEWS_TASK_QUEUE = os.environ.get("NEWS_TASK_QUEUE", "NewsTaskQueue")


@dataclass
class NewsfeedInput:
    '''List of topics as well as date to perform the search'''
    topicDate: str
    topicString: str
    previousResults: List[Dict]


