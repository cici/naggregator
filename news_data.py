import os
from dataclasses import dataclass, field

NEWS_TASK_QUEUE = os.environ.get("NEWS_TASK_QUEUE", "NewsTaskQueue")


@dataclass
class TopicInput:
    '''List of topics as well as date to perform the search'''
    topicDate: str
    topicString: str


@dataclass
class Article:
    '''Information about a particular article'''
    position: int
    source: str
    title: str
    link: str
    date: str
    thumbnail: str
    snippet: str


@dataclass
class EmailDetails:
    '''Information necessary to send notification email'''
    sender_email: str = "cicitestacct@gmail.com"
    receiver_email: str = ""
    port: int = 587
    smtp_host: str = "smtp.gmail.com"
    password: str = ""
