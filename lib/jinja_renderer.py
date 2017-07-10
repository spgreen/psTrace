import jinja2


def render_template_output(template_fp, **kwargs):
    """
    
    :param template_fp: template file path 
    :param kwargs: variables used within the template
    :return: rendered page
    """
    template_loader = jinja2.FileSystemLoader(searchpath=".")
    template_env = jinja2.Environment(loader=template_loader)
    template_file = template_fp
    try:
        template = template_env.get_template(template_file)
    except jinja2.exceptions.TemplateNotFound:
        print("Unable to find Jinja2 template")
        return
    return template.render(kwargs)
