import pickle
import os
from github import PullRequest, Repository

cachdir = "./cache/"


def load_prs(g, pr_dir):
    prs = []
    for filename in os.listdir(pr_dir):
        f = os.path.join(pr_dir, filename)
        with open(f, 'rb') as f1:
            loaded = pickle.load(f1)
            prs.append(g.create_from_raw_data(
                klass=PullRequest.PullRequest, raw_data=loaded))
    return prs


def dump_prs(prs, d):
    i = 0
    for pr in prs:
        filename = d + "/" + str(i) + ".raw"
        with open(filename, 'wb') as f2:
            pickle.dump(pr.raw_data, f2)
        i += 1


def cache_create(prs):
    os.mkdir(cachdir)
    for r in prs:
        repo_dir = cachdir + r["repo"].name
        pr_dir = repo_dir + "/prs"
        repo_obj = repo_dir + "/repo.raw"
        tr = repo_dir + "/tr.raw"
        prev = repo_dir + "/pr.raw"
        os.mkdir(repo_dir)
        os.mkdir(pr_dir)
        dump_prs(r["prs"], pr_dir)
        with open(repo_obj, "wb") as f:
            pickle.dump(r["repo"].raw_data, f)
        with open(tr, "wb") as f:
            pickle.dump(r["target_release"], f)
        with open(prev, "wb") as f:
            pickle.dump(r["previous_release"], f)


def cache_fetch(gh):
    prs = []
    for repo_name in os.listdir(cachdir):
        repo_dir = os.path.join(cachdir, repo_name)
        pr_dir = repo_dir + "/prs"
        repo_obj = repo_dir + "/repo.raw"
        tr = repo_dir + "/tr.raw"
        prev = repo_dir + "/pr.raw"

        repo_prs = load_prs(gh, pr_dir)

        with open(repo_obj, "rb") as f:
            loaded = pickle.load(f)
            gh_repo = gh.create_from_raw_data(klass=Repository.Repository,
                                              raw_data=loaded)
        with open(tr, "rb") as f:
            target_release = pickle.load(f)
        with open(prev, "rb") as f:
            previous_release = pickle.load(f)
        prs.append({
            "repo": gh_repo,
            "prs": repo_prs,
            "target_release": target_release,
            "previous_release": previous_release,
        })

    return prs
