# CHANGELOG

## 0.16.0 (2024-07-15)
* Add `.xls` support.

## 0.15.0 (2024-07-01)
* Fix a bug where S3 history was not working properly.

## 0.14.0 (2024-06-30)
* Add Spanish and Japanese language support.
* Add MySQL authentication support.
* Add S3 history support.

## 0.13.0 (2024-06-27)
* Add feature to hide quotation marks in File Search.

## 0.12.0 (2024-06-20)
* Add the `canu.list_runs` method.
* Add the `canu.is_thread_locked` method.
* Fix a bug where `openai.BadRequestError` was raised when messages were added while a run is active.

## 0.11.0 (2024-06-19)
* Add multi-language support.

## 0.10.0 (2024-06-15)
* Add the `canu.delete_files` method.
* Add feature to change the assistant's avatar image.

## 0.9.0 (2024-06-13)
* Fix a bug where `streamlit.errors.DuplicateWidgetID` was raised by the download button.
* Fix a bug where `openai.BadRequestError` was raised when an unsupported file was uploaded.

## 0.8.0 (2024-06-12)
* Add the `canu.list_messages` method.
* Add the `canu.delete_messages` method.
* Add the `canu.create_message` method.
* Add the `canu.Container.get_content` method.

## 0.7.0 (2024-06-11)
* Add the `canu.show_history_page` method.
* Add the `canu.EventHandler.redundant` attribute.
* Add the `canu.handle_files` method.
* Add the `canu.Container.code_interpreter_files` attribute.

## 0.6.0 (2024-06-09)
* Add the `canu.EventHandler.on_event` method.
* Add the `canu.EventHandler.on_tool_call_delta` method.
* Add the `canu.EventHandler.submit_tool_outputs` method.

## 0.5.0 (2024-06-08)
* Add the `canu.get_uploaded_files` method.
* Remove the `canu.set_page` method.

## 0.4.0 (2024-06-06)
* Rename the `canu.get_authenticator` method to `canu.authenticate`.
* Add the `canu.update_yaml_file` method.
* Add the `canu.show_login_page` method.
* Add the `canu.show_profile_page` method.
* Add the `canu.set_page` method.
* Remove the `canu.logout` method.

## 0.3.0 (2024-06-04)
* Add the `canu.functions.retrieve_from_web` method.
* Add the `canu.functions.generate_image` method.
* Add the `canu.EventHandler.on_image_file_done` method.

## 0.2.0 (2024-06-02)
* Add the `canu.write_stream` method.
* Add the `canu.logout` method.
* Add the `canu.EventHandler` class.

## 0.1.0 (2024-06-01)
* Initial release.