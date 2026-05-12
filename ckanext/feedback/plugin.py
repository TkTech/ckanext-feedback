import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.lib.plugins import DefaultTranslation

from ckanext.feedback.views import feedback_blueprint
from ckanext.feedback.admin import feedback_admin
from ckanext.feedback import helpers


class FeedbackPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.ITranslation)

    # IConfigurer
    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")
        tk.add_resource("assets", "ckanext_feedback")

    # IBlueprint
    def get_blueprint(self):
        return [feedback_blueprint, feedback_admin]

    # ITemplateHelpers
    def get_helpers(self):
        return {
            "feedback_rating_avg": helpers.feedback_rating_avg,
            "feedback_user_rating": helpers.feedback_user_rating,
            "feedback_recaptcha_site_key": helpers.feedback_recaptcha_site_key,
            "feedback_subject_types": helpers.feedback_subject_types,
            "feedback_reasons": helpers.feedback_reasons,
            "feedback_form_errors": helpers.feedback_form_errors,
            "feedback_form_data": helpers.feedback_form_data,
        }
