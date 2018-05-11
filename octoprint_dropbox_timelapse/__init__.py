# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError


class DropboxTimelapsePlugin(octoprint.plugin.SettingsPlugin,
                             octoprint.plugin.EventHandlerPlugin,
                             octoprint.plugin.TemplatePlugin):

    def get_settings_defaults(self):
        return dict(
            api_token=None,
            delete_after_upload=False
        )

    def get_settings_restricted_paths(self):
        return dict(
            admin=[['api_token'], ]
        )

    def get_template_configs(self):
        return [
            dict(type='settings', custom_bindings=False, template='dropbox_timelapse_settings.jinja2')
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

    def on_event(self, event, payload):
        from octoprint.events import Events
        if event == Events.MOVIE_DONE:
            self.upload_timelapse(payload)

    def upload_timelapse(self, payload):
        path = payload['movie']
        file_name = payload['movie_basename']
        if self.api_token:
            db = dropbox.Dropbox(self.api_token)
        else:
            self._logger.info('No Dropbox API Token Defined! Cannot Upload Timelapse %s!' % file_name)
            return

        delete = self.delete_after_upload

        try:
            db.users_get_current_account()
        except AuthError:
            self._logger.info('Invalid Dropbox API Token! Cannot Upload Timelapse %s!' % file_name)

        with open(path, 'rb') as f:
            self._logger.info('Uploading %s to Dropbox...' % file_name)
            try:
                db.files_upload(f.read(), '/'+file_name, mode=WriteMode('overwrite'))
                self._logger.info('Uploaded %s to Dropbox!' % file_name)
            except ApiError as e:
                delete = False
                if e.error.is_path() and e.error.get_path().error.is_insufficient_space():
                    self._logger.info('Cannot upload to Dropbox! Insufficient space on Dropbox!')
                elif e.user_message_text:
                    self._logger.info(e.user_message_text)
                else:
                    self._logger.info(e)
        if delete:
            import os
            self._logger.info('Deleting %s from local disk...' % file_name)
            os.remove(path)
            self._logger.info('Deleted %s from local disk.' % file_name)


__plugin_name__ = "Dropbox Timelapse Plugin"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = DropboxTimelapsePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }

