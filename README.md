Github-Jira-Automation
====================
Objective
---------
RHOAI is moving towards using github-issues for tracking all the items for a release, but we still need Jira tracking for adding these to advisory and also for QE to track the testing.
Objective of Github-Jira-Automation is to scrap and find the upstream github issues which are part of a RHODS downstream release, and automatically create one jira per component with list of identified github issues

Prerequisite:
------------
There are two ways Github-Jira-automation can find/correlate an upstream github issue with RHODS X.Y release:
* `rhods-X.Y` label added to the github issue
* PRs to the downstream release branches have relevant github issues linked

If any of the above is true for a github issue, it will be detected by the Github-Jira-automation.


Workflow
----------
* The tool is run on-demand using this [github-action](https://github.com/dchourasia/Github-JIRA-Automation/actions/workflows/githb-jira-automation.yaml) after code-freeze
* Entire workflow is run based on the configuration from [config yaml](https://github.com/dchourasia/Github-JIRA-Automation/blob/main/config/components.json)
* We compare the commits of current release branch with previous release branch and eliminate older ones to derive the commits which are unique to the current release
* These commits are correlated back to upstream commits/PRs, which in-turn are searched for linked github issues
* The scrapping logic is not branch dependent, we find the PR associated with the downstream commit and see if it's an upstream PR, if not we look if PR has any related upstream commits, if yes we scrap them to find the upstream PR, which in-turn gives us linked issues. So essentially if you have a manual commit which was only made to downstream, then we need to skip such commits. Also if you missed to link the github issue with PR then also the automation cannot find the issue
* We also explore and add github issues which have a label like *rhods-X.Y* 
* This automation creates one Jira per component based on this [config yaml](https://github.com/dchourasia/Github-JIRA-Automation/blob/main/config/components.json) 

Miscellaneous
----------
* No dependency on github-releases
* No requirement to have a strict one to one mapping between upstream and downstream releases
* Focusing on github issues rather than PRs because these will be referred by everyone including our customers

