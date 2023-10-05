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
from ghj_config import ghj_config
from collections import defaultdict
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

def build_msg_issues(issues: list, issue_titles:dict):
    # header = "Changes introduced for component {0}".format(repo_name)
    # sub_header = "Changes are between upstream tags {0}...{1}".format(previous_release, target_release)
    body = ''
    for issue in issues:
        if issue in issue_titles:
            body += f"# [{issue_titles[issue]} | {issue}] \n"
        else:
            body += f"# {issue} \n"

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



def fetch_issues(config:ghj_config, component:dict, commits_with_no_issue_ref:defaultdict(list), commits_without_pr:defaultdict(list), commits_directly_made_to_downstream:defaultdict(list), issue_titles:dict):
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

    def get_issues_for_org(upstream_org:str, gh:Github):
        issues = []
        issues = gh.search_issues(query=f'is:issue user:{upstream_org} label:{config.filter_labels}&per_page=100')





    def process_upstream_pr(upstream_org, upstream_PR:PullRequest, repo_issues:list, repo:str):
        if upstream_PR.number not in upstream_repo_prs:
            repo_issues += get_linked_issues(upstream_org, repo, upstream_PR, commits_with_no_issue_ref, issue_titles)
            upstream_repo_prs.append(upstream_PR.number)

    issues = []


    for repo in component["cpaas_repos"]:
        downstream_repo_prs = []
        upstream_repo_prs = []
        repo_issues = []
        upstream_org, downstream_org = config.upstream_org, config.downstream_org
        if '/' in repo:
            upstream_org, repo = repo.split('/')[0], repo.split('/')[1]
        downstream_repo = config.gh.get_organization(downstream_org).get_repo(repo)
        upstream_repo = config.gh.get_organization(upstream_org).get_repo(repo)
        previous_commits = downstream_repo.get_commits(sha=config.previous_release, since=datetime.datetime.today() - datetime.timedelta(days=60))
        current_commits = downstream_repo.get_commits(sha=config.target_release, since=datetime.datetime.today() - datetime.timedelta(days=45))

        target_commits = []
        for commit in current_commits:
            if commit not in previous_commits:
                target_commits.append(commit)
            else:
                break
        for downstream_commit in target_commits:
            try:
                pull_requests = downstream_commit.get_pulls()
                if pull_requests.totalCount > 0:
                    downstream_PR = downstream_commit.get_pulls().get_page(0).pop()
                    if get_github_org(downstream_PR.html_url) == upstream_org:
                        process_upstream_pr(upstream_org, downstream_PR, repo_issues, repo)
                    elif downstream_PR.number not in downstream_repo_prs:
                        process_upstream_pr(downstream_org, downstream_PR, repo_issues, repo)
                        upstream_commits = downstream_PR.get_commits()
                        for upstream_commit in upstream_commits:
                            if upstream_commit in target_commits:
                                commits_directly_made_to_downstream[repo].append(upstream_commit.html_url)
                                continue
                            upstream_PR = upstream_commit.get_pulls().get_page(0).pop()
                            process_upstream_pr(upstream_org, upstream_PR, repo_issues, repo)
                        downstream_repo_prs.append(downstream_PR.number)
                else:
                    commits_without_pr[repo].append(downstream_commit.html_url)
            except Exception as e:
                print(f'Exception while getting PR for the commit {downstream_commit.html_url}, skipping the commit')
                print(e)
                print(traceback.format_exc())
        repo_issues = list(set(repo_issues))
        issues += repo_issues

    return issues

def get_github_org(url:str):
    return url.split('/')[3] if url else ''

def get_linked_issues(upstream_org, repo, PR: PullRequest, commits_with_no_issue_ref:defaultdict(list), issue_titles:dict):
    issues = []
    try:
        pr_url = f"https://github.com/{upstream_org}/{repo}/pull/{PR.number}"
        r = requests.get(pr_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        issueForm = soup.find("form", {"aria-label": re.compile('Link issues')})
        issues = [i["href"] for i in issueForm.find_all("a")]
        # //bdi[contains(@class, 'js-issue-title')]
        for issue in issues:
            if issue not in issue_titles:
                try:
                    r = requests.get(issue)
                    soup = BeautifulSoup(r.text, 'html.parser')
                    issue_title = soup.find('bdi', {'class': 'js-issue-title'}).text
                    issue_titles[issue] = issue_title
                except Exception as e:
                    print(traceback.format_exc())
        if not issues:
            commits_with_no_issue_ref[repo].append(pr_url)
    except Exception as e:
        print(traceback.format_exc())

    return issues

def handle_jira_processing(config:ghj_config, jira_component, msg, summary):
    jira_issue = None
    if summary not in config.existing_jiras:
        issue_dict = {
            'project': {'key': config.jira_project},
            'summary': summary,
            'fixVersions': [config.jira_target_release.name],
            'description': msg,
            'issuetype': {'name': config.jira_issue_type},
            'labels': config.jira_labels,
            'priority': {'name': config.jira_priority},
            'components': [{'name': jira_component}],
            'customfield_12311240': {'id': config.jira_target_release.id}
        }

        # jira_issue = config.jc.create_issue(fields=issue_dict)
    else:
        issue_dict = {
            'description': msg
        }
        existing_jira = config.existing_jiras[summary]
        # existing_jira.update(fields=issue_dict)
        jira_issue = existing_jira.key
    return jira_issue



def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Create a Jira Issue from a GitHub tag release."
    )

    parser.add_argument("--dry_run", dest="dry_run",
                        action="store",
                        help="Use this flag to run the program in dry-run mode, means it will not create any Jiras", required=False, default="true")

    parser.add_argument("--config", dest="config",
                        help="A JSON config ]",
                        **env_opts("CONFIG"))

    parser.add_argument("--gh_token", dest="gh_token",
                        help="", **env_opts("GITHUB_TOKEN"))

    parser.add_argument("--jira_token", dest="jira_token",
                        help="", **env_opts("JIRA_TOKEN"))

    args = parser.parse_args()

    return args
def extract_issues_with_filter_labels(config:Github, filter_label_issues:defaultdict(list), issue_titles:dict):
    issues = []
    upstream_orgs = [config.upstream_org]
    upstream_orgs += list(set([repo.split('/')[0] for component in config.components for repo in component["cpaas_repos"] + component["non_cpaas_repos"] if '/' in repo]))
    for upstream_org in upstream_orgs:
        issues += config.gh.search_issues(query=f'is:issue user:{upstream_org} label:{config.filter_labels}')
    # component_repos = {component["component_name"]:list(set(component["cpaas_repos"] + component["non_cpaas_repos"])) for component in config.components}
    repos_component = {(repo if '/' not in repo else repo.split('/')[1]):component["component_name"] for component in config.components for repo in list(set(component["cpaas_repos"] + component["non_cpaas_repos"]))}
    for issue in issues:
        issue_titles[issue.html_url] = issue.title
        if issue.repository.name in repos_component:
            filter_label_issues[repos_component[issue.repository.name]].append(issue.html_url)
        else:
            filter_label_issues['Missing_Repos'].append(issue.html_url)

def main():
    args = parse_arguments()
    args.dry_run = False if args.dry_run == "false" else True
    config = ghj_config(args.config, args.gh_token, args.jira_token)

    commits_with_no_issue_ref, commits_without_pr, commits_directly_made_to_downstream, filter_label_issues = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    issue_titles = {}
    jiras_reported = []
    extract_issues_with_filter_labels(config, filter_label_issues, issue_titles)
    for component in config.components:
        component_name = component["component_name"]
        jira_component = component["jira_component"]
        print(f'******************* Starting Component {component_name} *******************')
        issues = fetch_issues(config, component, commits_with_no_issue_ref, commits_without_pr, commits_directly_made_to_downstream, issue_titles)
        issues = list(set(issues + filter_label_issues[component["component_name"]]))
        if issues:
            msg = build_msg_issues(issues, issue_titles)
            summary = config.jira_issue_title.format(component_name, config.target_release)
            print(summary, msg)
            # print(args.dry_run, type(args.dry_run))
            if not args.dry_run:
                jira_issue = handle_jira_processing(config, jira_component, msg, summary)
                print(f'Created https://issues.redhat.com/browse/{jira_issue} for component {jira_component}')
                jiras_reported.append(f'https://issues.redhat.com/browse/{jira_issue}')

        else:
            print('not enough github issues found for component {0} for release {1}'.format(component_name, config.target_release))
    print('commits_with_no_issue_ref', commits_with_no_issue_ref)
    print('commits_without_pr', commits_without_pr)
    print('commits_directly_made_to_downstream', commits_directly_made_to_downstream)
    if not args.dry_run:
        print('jiras reported/updated - ', jiras_reported)
    else:
        print('Dry-run enabled, no jira tickets created/updated.')
    print('Issues found for missing repos', filter_label_issues['Missing_Repos'])



if __name__ == "__main__":
    main()
