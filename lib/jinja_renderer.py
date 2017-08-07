import jinja2
import os


def render_template_output(template_fp, **template_variables):
    """
    Renders Jinja2 Templates with user submitted template variables
    :param template_fp: template file path
    :type template_fp: str
    :param template_variables: variables used within said template
    :type template_variables: str
    :return: rendered page or None if template could not be found
    """
    path, template_file = os.path.split(template_fp)
    # Sets path to current directory with "." if path variable is empty
    if not path:
        path = '.'
    template_loader = jinja2.FileSystemLoader(path)
    template_env = jinja2.Environment(loader=template_loader)
    try:
        template = template_env.get_template(template_file)
    except jinja2.exceptions.TemplateNotFound:
        print("Error: Unable to find Jinja2 template @ %s" % template_fp)
        return
    return template.render(template_variables)
