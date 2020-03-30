# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.events import Events
import os
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError, BadInputError


class DropboxTimelapsePlugin(octoprint.plugin.StartupPlugin,
                             octoprint.plugin.TemplatePlugin,
                             octoprint.plugin.SettingsPlugin,
                             octoprint.plugin.EventHandlerPlugin,
                             octoprint.plugin.AssetPlugin):

    def __init__(self):
        # fas
        self.upload_events = {}

    def _add_upload_event(self, event_name, payload_path_key):
        # make sure the event exists
        if hasattr(Events, event_name):
            event = getattr(Events, event_name)
            if event not in self.upload_events:
                self.upload_events[event] = payload_path_key
            else:
                self._logger.warning('Attempted to add a duplicate movie event: %s', event_name)
        else:
            self._logger.warning('Attempted to add an event that does not exist: %s', event_name)

    def _add_all_upload_events(self):
        # clear the events set
        self.upload_events = {}
        # add the stock timelapse event
        self.upload_events[Events.MOVIE_DONE] = 'movie'
        # add any additional movie events that are stored within the settings
        for additional_event in self.additional_upload_events:
            self._add_upload_event(additional_event['event_name'], additional_event['payload_path_key'])

    def on_after_startup(self):
        # now we can add all of the movie events since the settings are loaded.
        self._add_all_upload_events()

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        # the settings have changed, reload the movie events
        self._add_all_upload_events()

    def get_settings_defaults(self):
        return dict(
            api_token=None,
            delete_after_upload=False,
            additional_upload_events=[
                {
                    'event_name': 'PLUGIN_OCTOLAPSE_MOVIE_DONE',
                    'payload_path_key': 'movie'
                },
                {
                    'event_name': 'PLUGIN_OCTOLAPSE_SNAPSHOT_ARCHIVE_DONE',
                    'payload_path_key': 'archive'
                }
            ]
        )

    def get_settings_restricted_paths(self):
        return dict(
            admin=[['api_token'], ]
        )

    def get_template_configs(self):
        return [
            dict(type='settings', custom_bindings=True, template='dropbox_timelapse_settings.jinja2')
        ]

    def get_update_information(self):
        return dict(
            dropbox_timelapse=dict(
                displayName="Dropbox Timelapse Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="jslay88",
                repo="OctoPrint-Dropbox-Timelapse",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/jslay88/OctoPrint-Dropbox-Timelapse/archive/{target_version}.zip"
            )
        )

    @property
    def api_token(self):
        return self._settings.get(['api_token'])

    @property
    def delete_after_upload(self):
        return self._settings.get_boolean(['delete_after_upload'])

    @property
    def additional_upload_events(self):
        return self._settings.get(['additional_upload_events'])

    def on_event(self, event, payload):
        if event in self.upload_events:
            payload_path_key = self.upload_events[event]
            if payload_path_key in payload:
                file_path = payload[payload_path_key]
                file_name = os.path.basename(file_path)
                self._plugin_manager.send_plugin_message(
                    self._identifier, {'type': 'upload-start', 'file_name': file_name}
                )
                if self.upload_timelapse(file_path):
                    self._plugin_manager.send_plugin_message(
                        self._identifier, {'type': 'upload-success', 'file_name': file_name}
                    )
                else:
                    self._plugin_manager.send_plugin_message(
                        self._identifier, {'type': 'upload-failed', 'file_name': file_name}
                    )
            else:
                self._plugin_manager.send_plugin_message(
                    self._identifier, {'type': 'upload-failed', 'file_name': "UNKNOWN"}
                )
                self._logger.error(
                    "Unable to find the '%s' key within the %s event payload."
                    , payload_path_key, event
                )

    def upload_timelapse(self, path):
        # just use the path to get the file name.  This requires fewer settings, and a name might not exist
        # for every event we are interested in
        file_name = os.path.basename(path)

        if self.api_token:
            db = dropbox.Dropbox(self.api_token)
        else:
            self._logger.info('No Dropbox API Token Defined! Cannot Upload Timelapse %s!', file_name)
            return False

        delete = self.delete_after_upload

        try:
            db.users_get_current_account()
        except (
                AuthError, BadInputError
        ):
            # catch more errors
            self._logger.exception(
                'There was a problem authenticating to your Dropbox account.  Either the token is invalid, or it is '
                'not in the correct format.  Cannot Upload Timelapse %s!', file_name)
            return False

        with open(path, 'rb') as f:
            self._logger.info('Uploading %s to Dropbox...', file_name)
            try:
                db.files_upload(f.read(), '/'+file_name, mode=WriteMode('overwrite'))
                self._logger.info('Uploaded %s to Dropbox!', file_name)
            except ApiError as e:
                delete = False
                if e.error.is_path() and e.error.get_path().error.is_insufficient_space():
                    self._logger.info('Cannot upload to Dropbox! Insufficient space on Dropbox!')
                elif e.user_message_text:
                    self._logger.info(e.user_message_text)
                else:
                    self._logger.info(e)
                return False

        if delete:
            try:
                self._logger.info('Deleting %s from local disk...', file_name)
                os.remove(path)
                self._logger.info('Deleted %s from local disk.', file_name)
            except (OSError, IOError):
                self._logger.exception('Failed to delte %s from local disk.', file_name)
                self._plugin_manager.send_plugin_message(
                    self._identifier, {'type': 'delete-failed', 'file_name': file_name}
                )

        return True

    def get_assets(self):
        return dict(
            js=["js/settings.js"]
        )


__plugin_name__ = "Dropbox Timelapse Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = DropboxTimelapsePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }

