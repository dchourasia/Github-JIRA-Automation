import json
from github import Auth, PullRequest, Github, Repository
from jira import JIRA
class ghj_config:

    def __init__(self, config_file, gh_token, jira_token):
        config = json.load(config_file)
        self.target_release = config["target_release"]
        self.previous_release = config["previous_release"]
        self.upstream_org = config["upstream_org"]
        self.downstrean_org = config["downstrean_org"]
        self.labels_to_filter = config["labels"]

        self.jira_server = config["jira_server"]
        self.jira_project = config["jira_project"]
        self.jira_issue_type = config["jira_issue_type"]
        self.jira_labels = config["jira_labels"]
        self.jira_priority = config["jira_priority"]
        self.components = config["components"]
        auth = Auth.Token(gh_token)

        self.gh = Github(auth=auth)
        self.jc = JIRA(token_auth=jira_token, server=self.jira_server)
