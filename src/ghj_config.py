import json
from github import Auth, PullRequest, Github, Repository
from jira import JIRA
import os
class ghj_config:

    def __init__(self, config_file, gh_token, jira_token):
        print(os.getcwd())
        config = json.load(open(config_file))
        self.target_release = config["target_release"]
        self.previous_release = config["previous_release"]
        self.upstream_org = config["upstream_org"]
        self.downstream_org = config["downstream_org"]
        self.filter_labels = config["filter_labels"]

        self.jira_server = config["jira_server"]
        self.jira_project = config["jira_project"]
        self.jira_issue_type = config["jira_issue_type"]
        self.jira_labels = config["jira_labels"].split(',')
        self.jira_priority = config["jira_priority"]
        self.jira_target_release = config["jira_target_release"]
        self.jira_issue_title = 'Github Issues for Component {0} for release {1}'

        self.components = config["components"]
        auth = Auth.Token(gh_token)

        self.gh = Github(auth=auth)
        self.jc = JIRA(token_auth=jira_token, server=self.jira_server)
        self.jira_target_release = self.jc.get_project_version_by_name(project='RHODS', version_name=self.jira_target_release)
        self.existing_jiras = self.get_existing_jiras()
        self.existing_jiras = {jira.fields.summary:jira for jira in self.existing_jiras}
        # users = self.jc.search_users(query='.')
        a=1



    def get_existing_jiras(self):
        jiras = self.jc.search_issues(jql_str=f'project = "Red Hat OpenShift Data Science" and summary ~ "{self.jira_issue_title.format("*", self.target_release)}"')
        return jiras
