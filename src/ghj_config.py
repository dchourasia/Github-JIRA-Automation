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

        self.components = config["components"]
        auth = Auth.Token(gh_token)

        self.gh = Github(auth=auth)
        self.jc = JIRA(token_auth=jira_token, server=self.jira_server)
