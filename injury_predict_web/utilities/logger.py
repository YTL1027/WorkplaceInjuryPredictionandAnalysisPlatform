from django.utils import timezone

"""
This class helps format and create log messages in the console and web log information
"""


class Logger:
    def __init__(self, task_obj):
        self.task_obj = task_obj

    # TODO add date time
    def message(self, content):
        self.task_obj.log = "[{}]  {}<br>{}".format(
            timezone.localtime(timezone.now()).strftime("%X"),
            content,
            self.task_obj.log,
        )
        self.task_obj.save()
        print(content)
