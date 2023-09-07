import argparse
import datetime
import os
from github import Auth, PullRequest, Github, Repository
from jira import JIRA
from typing import List, Dict, Union
import json
import requests
from bs4 import BeautifulSoup
import re, traceback

def env_opts(env: str):
    if env in os.environ:
        return {'default': os.environ[env]}
    else:
        return {'required': True}


def build_msg_prs(prs: List[Dict[str, Union[Repository.Repository, str, PullRequest.PullRequest]]]):
    body = ""
    for repo in prs:
        repo_name = repo["repo"].name
        repo_prs = repo["prs"]
        if len(repo_prs) == 0:
            continue
        target_release = repo["target_release"]
        previous_release = repo["previous_release"]

        header = "Changes introduced for repo {0}".format(repo_name)
        sub_header = "Changes are between upstream tags {0}...{1}".format(previous_release, target_release)
        body += "h3. *{0}*\n".format(header)
        body += "{0}\n\n".format(sub_header)
        for pr in repo_prs:
            body += "* {0}\n{1}\n".format(pr.title, pr.html_url)
        body += "\n"

    body += "This issue was auto generated."
    return body

def build_msg_issues(issues: list):
    # header = "Changes introduced for component {0}".format(repo_name)
    # sub_header = "Changes are between upstream tags {0}...{1}".format(previous_release, target_release)
    body = ''
    for issue in issues:
        body += f"* {issue} \n"

    return body
def fetch_prs(gh: Github,
              repos: List[Dict[str, str]],
              org: str,
              labels_to_filter: List[str]):
    """
    Fetch all PRS associated with the commits between previous_release and
    target_release tags. If 2 commits are associated with a single pr,
    duplicate is ignored. Only prs with labels labels_to_filter are considered.

    Return prs organized by repos they belong to.

    :param gh:
    :param repos:
    :param org:
    :param previous_release:
    :param target_release:
    :param labels_to_filter:
    :return:
    """

    prs = []

    def filter_labels(label_name):
        return label_name in labels_to_filter

    for repo in repos:
        repo_prs = []

        gh_repo = gh.get_organization(org).get_repo(repo["repo_name"])
        previous_release = repo["previous_release"]
        target_release = repo["target_release"]
        compare_results = gh_repo.compare(previous_release, target_release)

        for commit in compare_results.commits:
            pull_requests = commit.get_pulls()
            for pr in pull_requests:
                has_verify = any(filter_labels(label.name) for label in pr.labels)
                if has_verify and (pr not in repo_prs):
                    repo_prs.append(pr)
        prs.append({
            "repo": gh_repo,
            "prs": repo_prs,
            "target_release": target_release,
            "previous_release": previous_release,
        })
    return prs



def fetch_issues(gh: Github,
              repos: List[Dict[str, str]],
              org: str,
              labels_to_filter: List[str]):
    """
    Fetch all Github Issues associated with the commits between previous_release and
    target_release tags. If 2 commits are associated with a single pr,
    duplicate is ignored. Only prs with labels labels_to_filter are considered.

    Return prs organized by repos they belong to.

    :param gh:
    :param repos:
    :param org:
    :param previous_release:
    :param target_release:
    :param labels_to_filter:
    :return:
    """
    def filter_labels(label_name):
        return label_name in labels_to_filter
    issues = []
    for repo in repos:
        repo_prs = []
        repo_issues = []
        upstream_org = 'opendatahub-io'
        previous_release = repo["previous_release"]
        target_release = repo["target_release"]
        downstream_repo = gh.get_organization(org).get_repo(repo["repo_name"])
        upstream_repo = gh.get_organization(upstream_org).get_repo(repo["repo_name"])
        previous_commits = downstream_repo.get_commits(sha=previous_release, since=datetime.datetime.today() - datetime.timedelta(days=45))
        current_commits = downstream_repo.get_commits(sha=target_release, since=datetime.datetime.today() - datetime.timedelta(days=30))

        target_commits = []
        for commit in current_commits:
            if commit not in previous_commits:
                target_commits.append(commit)
            else:
                break
        for commit in target_commits:
            PR = commit.get_pulls().get_page(0).pop()
            if PR.number not in repo_prs:
                repo_issues += get_linked_issues(upstream_org, repo, PR)
                repo_prs.append(PR.number)
        repo_issues = list(set(repo_issues))
        # repo_issues = [issue.split('/')[-1] for issue in repo_issues]
        # repo_issues = [upstream_repo.get_issue(issue) for issue in repo_issues]
        issues += repo_issues

    return issues

def get_linked_issues(upstream_org, repo, PR: PullRequest):
    issues = []


    try:
        r = requests.get(f"https://github.com/{upstream_org}/{repo['repo_name']}/pull/{PR.number}")
        soup = BeautifulSoup(r.text, 'html.parser')
        issueForm = soup.find("form", {"aria-label": re.compile('Link issues')})
        issues = [i["href"] for i in issueForm.find_all("a")]
    except Exception as e:
        print(traceback.format_exc())
    return issues

def submit_jira(jc: JIRA, downstream_release: str, project: str, summary: str, description: str,
                issuetype: str, labels: str, priority: str):

    issue_dict = {
        'project': {'key': project},
        'summary': summary,
        'description': description,
        'issuetype': {'name': issuetype},
        'labels': labels,
        'priority': {'name': priority},
    }

    new_issue = jc.create_issue(fields=issue_dict)
    return new_issue


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Create a Jira Issue from a GitHub tag release."
    )

    parser.add_argument("--component", dest="component", help="ODH Component name, used in Jira title.", required=False, default='Build and Release')
    parser.add_argument("--target_release", dest="target_release",
                        help="Downstream Release target, should match Jira 'Target Release' field.", required=False, default='RHODS_1.33.0_GA')
    parser.add_argument("--org", dest="organization", help="Downstream GitHub Org", required=False, default='red-hat-data-services')
    parser.add_argument("--labels", dest="pr_filter_labels",
                        help="Upstream labels used to select on the GH issues to include in target Jira issue."
                             "Delimited by comma (,).",
                        required=False, default='')
    parser.add_argument("--jira_server", dest="jira_server", help="Jira Server to connect to.", required=False, default='https://issues.redhat.com/')
    parser.add_argument("--jira_project", dest="jira_project", help="Jira Project", required=False, default='RHODS')
    parser.add_argument("--jira_labels", dest="jira_labels", help="Jira Labels to add to the Jira issue. "
                                                                  "Delimited by comma (,).", required=False, default='eng,groomed')
    parser.add_argument("--jira_issue_type", dest="jira_issue_type", help="Jira Issue Type (E.g. Story, Task, etc.)",
                        required=False, default='Bug')

    parser.add_argument("--jira_priority", dest="jira_priority", help="Jira Priority, defaults to Normal.",
                        default='Normal', required=False)

    parser.add_argument("--dev", dest="dev",
                        action="store_true",
                        help="Use this flag to store gh data in cache after first run. This will "
                             "reduce the number of api calls made to the GH api in consecutive runs.", required=False)

    parser.add_argument("--repos", dest="repos",
                        help="A JSON of the form [ { repo_name: { previous_release: str, target_release)}, .. ]",
                        **env_opts("REPOS"))

    parser.add_argument("--gh_token", dest="gh_token",
                        help="", **env_opts("GITHUB_TOKEN"))

    parser.add_argument("--jira_token", dest="jira_token",
                        help="", **env_opts("JIRA_TOKEN"))

    args = parser.parse_args()

    return args


def main():
    args = parse_arguments()

    target_release = args.target_release
    component = args.component
    organization = args.organization
    repos = json.loads(args.repos)
    labels_to_filter = args.pr_filter_labels.split(",")
    gh_token = args.gh_token

    jira_server = args.jira_server
    jira_project = args.jira_project
    jira_issue_type = args.jira_issue_type
    jira_labels = args.jira_labels.split(',')
    jira_priority = args.jira_priority
    jira_token = args.jira_token

    auth = Auth.Token(gh_token)

    gh = Github(auth=auth)
    jc = JIRA(token_auth=jira_token, server=jira_server)

    if args.dev:
        from src.util import cache_create, cache_fetch
        if not os.path.exists("./cache"):
            prs = fetch_prs(gh, repos, organization, labels_to_filter)
            cache_create(prs)
        prs = cache_fetch(gh)
    else:
        # prs = fetch_prs(gh, repos, organization, labels_to_filter)
        issues = fetch_issues(gh, repos, organization, labels_to_filter)

    msg = build_msg_issues(issues)
    summary = "Github Issues for Component {0} for release {1}".format(component, target_release)
    print(msg)

    new_jira = submit_jira(
        jc=jc,
        project=jira_project,
        summary=summary,
        description=msg,
        issuetype=jira_issue_type,
        labels=jira_labels,
        priority=jira_priority,
        downstream_release=target_release,
    )
    print(new_jira)

if __name__ == "__main__":
    main()
