import json
import os.path

import jinja2


class Jinja2Template:

    def __init__(self, jinja_template_file_path):
        self.jinja_template_fp = jinja_template_file_path

    def render_template_output(self, **template_variables):
        """
        Renders Jinja2 Templates with user submitted template variables
        :param template_variables: variables used within said template
        :return: rendered page or None if template could not be found
        """
        path, template_file = os.path.split(self.jinja_template_fp)
        # Sets path to current directory with "." if path variable is empty
        if not path:
            path = '.'
        template_loader = jinja2.FileSystemLoader(path)
        template_env = jinja2.Environment(loader=template_loader)
        try:
            template = template_env.get_template(template_file)
        except jinja2.exceptions.TemplateNotFound:
            print("Error: Unable to find Jinja2 template @ %s" % self.jinja_template_fp)
            return
        return template.render(template_variables)


class DataStore:

    def __init__(self):
        self.data_store = {}

    def update_from_json_file(self, file_path):
        """
        Updates dictionary with from a JSON file
        :param file_path: file path of the JSON file to load
        :return:
        """
        try:
            with open(file_path, "r") as file:
                self.data_store.update(json.load(fp=file))
        except FileNotFoundError:
            print("File %s not found!" % file_path)
        except ValueError:
            print("Error: Unable to update due to different dictionary_contents length")

    def save_as_json_file(self, file_path):
        """
        Saves the main data store in JSON format to the file path provided by file_path.
        :param file_path: file path of JSON to be saved
        :return:
        """
        try:
            with open(file_path, "w") as file:
                json.dump(obj=self.data_store, fp=file, indent=4)
        except FileNotFoundError:
            print("Directory %s does not exist. File not saved!" % file_path)
        return

    def get_data(self):
        """
        :return: data dictionary
        """
        return self.data_store
