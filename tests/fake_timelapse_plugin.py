from __future__ import absolute_import, unicode_literals

import os
from uuid import uuid4

import octoprint.plugin
from octoprint.events import Events, eventManager


class FakeTimelapse(octoprint.plugin.EventHandlerPlugin):
    def on_event(self, event, payload):
        if event == Events.PRINT_DONE:
            self._logger.info('PRINT FINISHED. SUBMITTING FAKE TIMELAPSE')
            eventManager().fire(Events.MOVIE_DONE, {
                'gcode': payload['name'],
                'movie': os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    'test.mp4'
                ),
                'movie_basename': 'test-%s.mp4' % str(uuid4())
            })


__plugin_name__ = 'Fake Timelapse'
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = FakeTimelapse()
