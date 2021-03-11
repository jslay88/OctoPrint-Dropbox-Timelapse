$(function() {
    // A custom ViewModel for holding custom upload events
    function AdditionalUploadEventViewModel(event_name, payload_path_key){
        var self = this;
        self.event_name = ko.observable(event_name);
        self.payload_path_key = ko.observable(payload_path_key);
    }
    function YoutubeTimelapseSettingsViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        self.settingsViewModel = parameters[0];
        self.cert_saved = ko.observable(false);
        self.cert_authorized = ko.observable(false);
        self.authorizing = ko.observable(false);
        self.cert_file_name = ko.observable('');
        self.cert_file_data = undefined;
        self.uploading_videos = ko.observable(false);
        self.videos_folder = ko.observable('/home/pi/.octoprint/timelapse');
        self.auth_code = ko.observable('');
        self.auth_url = ko.observable('#');
        self.valid_privacy_statuses = ko.observableArray([
          { name : 'Private', value : 'private' },
          { name : 'Unlisted', value : 'unlisted' },
          { name : 'Public', value : 'public' }
        ]);

        var certFileuploadOptions = {
            dataType: "json",
            maxNumberOfFiles: 1,
            autoUpload: false,
            headers: OctoPrint.getRequestHeaders(),
            add: function(e, data) {
                if (data.files.length === 0) {
                    // no files? ignore
                    return false;
                }

                self.cert_file_name(data.files[0].name);
                self.cert_file_data = data;
            },
            done: function() {
                self.cert_file_name(undefined);
                self.cert_file_data = undefined;
            }
        };

        $("#youtube_timelapse_cert_file").fileupload(certFileuploadOptions);

        self.uploadCertFile = function(){
            if (self.cert_file_data === undefined) return;
            self.authorizing(true);
            var file, fr;

            if (typeof window.FileReader !== 'function') {
              alert("The file API isn't supported on this browser yet.");
              self.authorizing(false);
              return;
            }

            file = self.cert_file_data.files[0];
            fr = new FileReader();
            fr.onload = receivedText;
            fr.readAsText(file);

            function receivedText(e) {
                let lines = e.target.result;
                var json_data = JSON.parse(lines);
                $.ajax({
                    url: API_BASEURL + "plugin/youtube_timelapse",
                    type: "POST",
                    dataType: "json",
                    data: JSON.stringify({command: "gen_secret", json_data: json_data}),
                    contentType: "application/json; charset=UTF-8"
                }).done(function(data){
                    if(data.cert_saved){
                        self.cert_saved(true);
                        self.auth_url(data.url);
                        self.authorizing(false);
                    }
                }).fail(function(){
                    console.log("error uploading cert file");
                    self.authorizing(false);
                });
            }
        }

        self.uploadVideos = function(){
            if (self.videos_folder() === undefined) return;

            self.uploading_videos(true);

            var upload_videos_delete_after = $('#upload_videos_delete_after').is(":checked");

            $.ajax({
                url: API_BASEURL + "plugin/youtube_timelapse",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({command: "upload_videos", videos_folder: self.videos_folder(), upload_videos_delete_after: upload_videos_delete_after}),
                contentType: "application/json; charset=UTF-8"
            }).done(function(){
                self.uploading_videos(false);
            }).fail(function(){
                console.log("error uploading videos");
                self.uploading_videos(false);
            });
        }

        self.authorizeCertFile = function(){
            if(self.auth_code() === '') return;
            self.authorizing(true);
            $.ajax({
                url: API_BASEURL + "plugin/youtube_timelapse",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({command: "authorize", auth_code: self.auth_code()}),
                contentType: "application/json; charset=UTF-8"
            }).done(function(data){
                if(data.authorized){
                    self.cert_authorized(true);
                    self.authorizing(false);
                }
            }).fail(function(){
                console.log("error authorizing");
                self.cert_authorized(false);
                self.authorizing(false);
            });
        }

        self.deleteCertFiles = function(){
            self.cert_saved(false);
            self.cert_authorized(false);
        }

        self.settings = parameters[0];
        self.plugin_settings = null;

        self.onBeforeBinding = function() {
            // Make plugin setting access a little more terse
            self.plugin_settings = self.settings.settings.plugins.youtube_timelapse;
            self.cert_saved(self.settingsViewModel.settings.plugins.youtube_timelapse.cert_saved());
            self.cert_authorized(self.settingsViewModel.settings.plugins.youtube_timelapse.cert_authorized());
        };
        // Add a custom event
        self.addUploadEvent = function() {
            self.plugin_settings.additional_upload_events.push(
                new AdditionalUploadEventViewModel("","")
            );
        };
        // Remove a custom event
        self.removeUploadEvent = function(index) {
            self.plugin_settings.additional_upload_events.splice(index, 1);
        };

        self.Popups = {};

        // Listen for plugin messages
        // This could probably be made a bit simpler.
        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "youtube_timelapse") {
                return;
            }

            var popup_options = {};

            switch (data.type) {
                case 'upload-start':
                {
                    popup_options = {
                        title: 'Uploading to Youtube...',
                        text: '\'' + data.file_name + '\' is uploading to Youtube now.',
                        type: 'info',
                        hide: true,
                        desktop: {
                            desktop: true
                        }
                    };
                    // Show at most one of these at a time.
                    self.displayPopupForKey(popup_options,data.type, [data.type]);
                    break;
                }
                case 'upload-success':
                {
                    popup_options = {
                        title: 'Youtube upload complete!',
                        text: '\'' + data.file_name + '\' was uploaded to Youtube successfully!.',
                        type: 'success',
                        hide: false,
                        desktop: {
                            desktop: true
                        }
                    };
                     self.displayPopup(popup_options);
                     // Close the upload-start popup if it hasn't closed already to keep things clean
                     self.closePopupsForKeys('upload-start');
                    break;
                }
                case 'upload-failed':
                {
                    popup_options = {
                        title: 'Youtube upload failed!',
                        text: '\'' + data.file_name + '\' failed to upload to Youtube!  Please check plugin_youtube_timelapse.log for more details.',
                        type: 'error',
                        hide: false,
                        desktop: {
                            desktop: true
                        }
                    };
                     self.displayPopup(popup_options);
                     // Close the upload-start popup if it hasn't closed already to keep things clean
                     self.closePopupsForKeys('upload-start');
                    break;
                }
                case 'delete-failed':
                {
                    popup_options = {
                        title: 'Delete After Youtube Upload failed!',
                        text: '\'' + data.file_name + '\' could not be deleted.  Please check plugin_youtube_timelapse.log for more details.',
                        type: 'error',
                        hide: false,
                        desktop: {
                            desktop: true
                        }
                    };
                     self.displayPopup(popup_options);
                     // No need to close the upload-start popup if it hasn't closed already here, since the success/fail
                    // popup will take care of that!
                    break;
                }
                default:
                    console.error("youtube_timelapse - An unknown plugin message type of " + data.type + "was received.");
                    break;
            }
        };

        self.displayPopup = function(options)
        {
            options.width = '450px';
            new PNotify(options);
        };

        // Show at most one popup for a given key, close any popups with the keys provided.
        self.displayPopupForKey = function (options, popup_key, remove_keys) {
            self.closePopupsForKeys(remove_keys);
            options.width = '450px';
            var popup = new PNotify(options);
            self.Popups[popup_key] = popup;
            return popup;
        };

        self.closePopupsForKeys = function (remove_keys) {
            if (!$.isArray(remove_keys)) {
                remove_keys = [remove_keys];
            }
            for (var index = 0; index < remove_keys.length; index++) {
                var key = remove_keys[index];
                if (key in self.Popups) {
                    var notice = self.Popups[key];
                    if (notice.state === "opening") {
                        notice.options.animation = "none";
                    }
                    notice.remove();
                    delete self.Popups[key];
                }
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        YoutubeTimelapseSettingsViewModel,
        ["settingsViewModel"],
        ["#settings_plugin_youtube_timelapse"]
    ]);
});
